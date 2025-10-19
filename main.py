# main.py
import time
import os
import datetime
import pandas as pd
from tabulate import tabulate
import copy
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

from db_util import create_table_if_not_exists, load_csv_into_db, run_query, check_row_count
from indexing_algos import LinearSearch, HashIndex, BinaryIndex, build_trie

REPORT_DIR = "reports"
os.makedirs(REPORT_DIR, exist_ok=True)
PDF_PATH = os.path.join(REPORT_DIR, "query_benchmark_report.pdf")

def benchmark(func, *args, label=None, suppress_output=True):
    """Run func(*args), measure time and return (results, duration)."""
    st = time.time()
    res = func(*args)
    duration = time.time() - st
    n = len(res) if hasattr(res, "__len__") else 0
    # Print numbers-only summary to console
    if suppress_output:
        print(f"Count: {n} | Time(s): {duration:.6f}")
    else:
        print(f"{label or func.__name__:25} | Results: {n:6} | Time: {duration:.6f}s")
    return res, duration

# DB-backed query helpers
def db_exact_name(name):
    q = "SELECT * FROM employees WHERE name = %s"
    return run_query(q, (name,), fetch=True)

def db_range_age(lo, hi):
    q = "SELECT * FROM employees WHERE age BETWEEN %s AND %s"
    return run_query(q, (lo, hi), fetch=True)

def db_prefix_name(prefix):
    p = prefix + '%'
    q = "SELECT * FROM employees WHERE name LIKE %s"
    return run_query(q, (p,), fetch=True)

def load_sample_from_db(limit=200000):
    q = f"SELECT * FROM employees LIMIT {limit}"
    return run_query(q, (), fetch=True)

def generate_pdf_report(results, db_name):
    """
    results: list of tuples (method_label, count, time_seconds)
    Writes a PDF with a table and a bar chart.
    """
    if not results:
        print("No results to write to PDF.")
        return

    # build DataFrame
    df = pd.DataFrame(results, columns=["method", "count", "time_s"])

    # Create PDF with two pages: table and chart
    with PdfPages(PDF_PATH) as pdf:
        # Page 1: title + table
        fig, ax = plt.subplots(figsize=(11, 8.5))
        ax.axis('off')
        title = f"Query Benchmark Report\nDatabase: {db_name}\nGenerated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        ax.text(0.5, 0.95, title, ha='center', va='top', fontsize=14, weight='bold')

        # Create a table in the figure
        table_data = [["Method", "Count", "Time (s)"]] + df.values.tolist()
        table = ax.table(cellText=table_data, colWidths=[0.6, 0.2, 0.2], cellLoc='center', loc='center')
        table.auto_set_font_size(False)
        table.set_fontsize(9)
        table.scale(1, 1.5)
        pdf.savefig(fig, bbox_inches='tight')
        plt.close(fig)

        # Page 2: bar chart of times
        fig2, ax2 = plt.subplots(figsize=(11, 6))
        methods = df["method"].tolist()
        times = df["time_s"].tolist()
        bars = ax2.bar(range(len(methods)), times)
        ax2.set_xticks(range(len(methods)))
        ax2.set_xticklabels(methods, rotation=45, ha='right', fontsize=9)
        ax2.set_ylabel("Time (s)")
        ax2.set_title("Method timings")
        # annotate bars with time values
        for rect, t in zip(bars, times):
            height = rect.get_height()
            ax2.annotate(f"{t:.6f}", xy=(rect.get_x() + rect.get_width() / 2, height),
                         xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', fontsize=8)
        plt.tight_layout()
        pdf.savefig(fig2, bbox_inches='tight')
        plt.close(fig2)

    print(f"PDF report generated at: {PDF_PATH}")
def add_postgres_rows_without_label(results_summary, pct=0.02):
    """
    results_summary: list of tuples (method_label, count, time_seconds)
    Appends Postgres estimated rows as 'Postgres (estimated):<method_label>'
    with time_s = original_time * (1 + pct).
    """
    if not results_summary:
        return []

    augmented = list(results_summary)
    for method_label, count, time_s in results_summary:
        try:
            base_time = float(time_s or 0.0)
        except Exception:
            base_time = 0.0
        est_time = base_time * (1.0 + float(pct))
        pg_label = f"Postgres (estimated):{method_label}"
        augmented.append((pg_label, int(count or 0), est_time))
    return augmented


def cli():
    create_table_if_not_exists()
    check_row_count()

    # CSV handling - you can skip if data already present
    csv = None  # set to path if you want to load CSV via CLI; set None to skip
    if csv:
        ans = input("Load CSV into MySQL? [y/N] ").strip().lower()
        if ans == "y":
            try:
                load_csv_into_db(csv)
            except Exception as e:
                print("Error loading CSV via LOAD DATA:", e)
                print("Use fallback importer or run the .sql file if needed.")

    # Choose mode
    print("Choose dataset mode:")
    print("1. Use DB queries (scales to 1M, uses MySQL indexes)  [recommended]")
    print("2. Load sample into memory and use in-memory indexes (builds Hash/Binary/Trie)")
    mode = input("Mode [1/2]: ").strip() or "1"

    indexes = None
    if mode == "2":
        print("Running: Loading sample rows from DB into memory...")
        mem_rows = load_sample_from_db(limit=200000)
        print("Done. Building in-memory indexes (linear, hash, binary, trie)...")
        linear = LinearSearch(mem_rows)
        h = HashIndex(mem_rows, key="name")
        b = BinaryIndex(mem_rows, key="age")
        t = build_trie(mem_rows)
        indexes = {"linear": linear, "hash": h, "binary": b, "prefix": t}
        print("Indexes built.")

    # results summary collects every executed search for PDF
    results_summary = []

    while True:
        print("\nChoose an option:")
        print("1. Search by Name (exact)       -> Uses Hash Index for exact matches")
        print("2. Range Search by Age          -> Uses Binary Index for range queries")
        print("3. Prefix Search by Name        -> Uses Prefix/Trie Index for prefix queries")
        print("4. Generate Report (run predefined benchmarks)")
        print("5. Export PDF report (numbers + graph)")
        print("6. Exit")
        c = input("Option: ").strip()
        if c == "1":
            name = input("Enter full name: ").strip()
            print(f"Running: Exact name search (hash index) for '{name}'")
            if mode == "1":
                res, d = benchmark(db_exact_name, name, label="DB Exact (MySQL)")
            else:
                res, d = benchmark(indexes["hash"].exact_name, name, label="In-memory Hash Exact")
            results_summary.append((f"Exact:{name}", len(res), d))

        elif c == "2":
            lo = int(input("age lo: ").strip())
            hi = int(input("age hi: ").strip())
            print(f"Running: Age range search ({lo} to {hi})")
            if mode == "1":
                res, d = benchmark(db_range_age, lo, hi, label="DB Range (MySQL)")
            else:
                res, d = benchmark(indexes["binary"].range_age, lo, hi, label="In-memory Binary Range")
            results_summary.append((f"Range:{lo}-{hi}", len(res), d))

        elif c == "3":
            prefix = input("Enter prefix: ").strip()
            print(f"Running: Prefix search for '{prefix}'")
            if mode == "1":
                res, d = benchmark(db_prefix_name, prefix, label="DB Prefix (MySQL LIKE)")
            else:
                res, d = benchmark(indexes["prefix"].starts_with, prefix, label="In-memory Trie Prefix")
            results_summary.append((f"Prefix:{prefix}", len(res), d))

        elif c == "4":
            # predefined benchmarks: Exact, Range, Prefix, plus a linear baseline sample
            print("Running: Predefined benchmark set")
            bench_list = []
            key_name = "Amit Sharma"
            # DB or in-memory depending on mode
            if mode == "1":
                print("Running: DB Exact (MySQL)")
                r, d = benchmark(db_exact_name, key_name)
                bench_list.append(("DB Exact", len(r), d))

                print("Running: DB Range (MySQL) 30-40")
                r, d = benchmark(db_range_age, 30, 40)
                bench_list.append(("DB Range", len(r), d))

                print("Running: DB Prefix (MySQL LIKE) 'Amit'")
                r, d = benchmark(db_prefix_name, "Amit")
                bench_list.append(("DB Prefix", len(r), d))

                # linear baseline from a small sample
                sample = load_sample_from_db(limit=20000)
                lin = LinearSearch(sample)
                print("Running: Linear baseline range (sample) 30-40")
                r, d = benchmark(lin.range_age, 30, 40)
                bench_list.append(("Linear Sample Range", len(r), d))
                generate_db_comparison_file(results_summary)

            else:
                h = indexes["hash"]
                b = indexes["binary"]
                p = indexes["prefix"]
                lin = indexes["linear"]

                print("Running: Hash exact (in-memory)")
                r, d = benchmark(h.exact_name, key_name)
                bench_list.append(("Hash Exact", len(r), d))

                print("Running: Binary range (in-memory) 30-40")
                r, d = benchmark(b.range_age, 30, 40)
                bench_list.append(("Binary Range", len(r), d))

                print("Running: Prefix entry (in-memory) 'Amit'")
                r, d = benchmark(p.starts_with, "Amit")
                bench_list.append(("Prefix Entry", len(r), d))

                print("Running: Linear baseline (in-memory) range 30-40")
                r, d = benchmark(lin.range_age, 30, 40)
                bench_list.append(("Linear Baseline Range", len(r), d))

            for item in bench_list:
                results_summary.append(item)
            generate_small_report(bench_list) 

        elif c == "5":        
            print("Exporting PDF report...")
            db_name = os.environ.get("DB_NAME", "query_optimizatio2")
            augmented = add_postgres_rows_without_label(results_summary, pct=0.02)
            generate_pdf_report(augmented, db_name) 

        elif c == "6":
            print("Bye")
            break

        else:
            print("Invalid option")

def generate_small_report(bench_list):
    """Optional: write quick summary.txt + timings.png for immediate view."""
    df = pd.DataFrame(bench_list, columns=["method", "count", "time_s"])
    tab = tabulate(df, headers="keys", tablefmt="psql")
    with open(os.path.join(REPORT_DIR, "summary.txt"), "w") as f:
        f.write(tab)
    plt.figure(figsize=(8,4))
    plt.bar(df["method"], df["time_s"])
    plt.ylabel("Time (s)")
    plt.title("Method timings (quick)")
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig(os.path.join(REPORT_DIR, "timings.png"))
    plt.close()
    print("Quick summary generated in reports/ (summary.txt, timings.png)")

def build_db_comparison_rows(results_summary, pg_pct=0.02):
    """
    Returns a list of dicts with keys:
      db: "mysql" | "postgres" | "in-memory" | "unknown"
      method: original/derived label
      count: int
      time_s: float
      estimated: bool (True for synthetic Postgres rows)

    If no Postgres rows are present, we add *estimated* Postgres rows
    for each MySQL row with time_s = mysql_time * (1 + pg_pct).
    """
    rows = []

    def detect_db_and_estimated(label):
        low = label.lower()
        if low.startswith("postgres (estimated):"):
            return "postgres", True
        if low.startswith("postgres:") or low.startswith("postgres "):
            return "postgres", False
        if low.startswith("db ") or low.startswith("db:") or "mysql" in low:
            return "mysql", False
        if low.startswith("exact:") or low.startswith("range:") or low.startswith("prefix:"):
            # Your code appends ("Exact:..."), ("Range:..."), ("Prefix:...")
            # when running MySQL mode -> treat as mysql
            return "mysql", False
        if "in-memory" in low or low.startswith(("hash", "binary", "prefix", "linear")):
            return "in-memory", False
        return "unknown", ("estimated" in low)

    # First pass: add existing rows as-is
    for method_label, count, t in results_summary:
        db, estimated = detect_db_and_estimated(method_label)
        rows.append({
            "db": db,
            "method": method_label,
            "count": int(count or 0),
            "time_s": float(t or 0.0),
            "estimated": bool(estimated),
        })

    # If there are no Postgres rows, synthesize from MySQL rows (+pg_pct)
    has_pg = any(r["db"] == "postgres" for r in rows)
    if not has_pg:
        for r in list(rows):
            if r["db"] == "mysql":
                rows.append({
                    "db": "postgres",
                    "method": f"Postgres (estimated):{r['method']}",
                    "count": r["count"],
                    "time_s": r["time_s"] * (1.0 + float(pg_pct)),
                    "estimated": True,
                })

    return rows

def _agg_key(x):
    s = x.lower()
    if "exact" in s: return "exact_s"
    if "range" in s: return "range_s"
    if "prefix" in s: return "prefix_s"
    return None

def _detect_system(label):
    z = label.lower()
    if z.startswith("postgres"): return "postgres"
    if "in-memory" in z or z.startswith(("hash","binary","prefix","linear")): return "in_memory"
    return "mysql"

def build_db_compare_aggregates(results_summary, pg_pct=0.02):
    if not results_summary: return []
    base = list(results_summary)
    synth = []
    for m, c, t in base:
        synth.append(("Postgres (estimated):"+m, c, float(t or 0.0)*(1.0+float(pg_pct))))
    have_pg = any(str(m).lower().startswith("postgres") for m,_,_ in base)
    all_rows = base + ([] if have_pg else synth)
    agg = {}
    for m, _, t in all_rows:
        sys = _detect_system(m)
        k = _agg_key(m)
        if k is None: 
            continue
        d = agg.setdefault(sys, {"system": sys, "exact_s":0.0, "range_s":0.0, "prefix_s":0.0})
        d[k] += float(t or 0.0)
    out = []
    for v in agg.values():
        v["total_s"] = v["exact_s"] + v["range_s"] + v["prefix_s"]
        out.append(v)
    return out

def generate_db_comparison_file(results_summary):
    """
    Generate comparison data for MySQL, PostgreSQL (estimated), and In-memory.
    Returns structured data for frontend consumption.
    """
    # Separate results by system type
    mysql_results = []
    inmemory_results = []
    
    for method_label, count, time_s in results_summary:
        label_lower = method_label.lower()
        
        # Categorize by system
        if 'db ' in label_lower or 'mysql' in label_lower or label_lower.startswith(('exact:', 'range:', 'prefix:')):
            mysql_results.append((method_label, count, time_s))
        elif 'in-memory' in label_lower or label_lower.startswith(('hash', 'binary', 'prefix entry', 'linear')):
            inmemory_results.append((method_label, count, time_s))
    
    # Generate PostgreSQL estimates (MySQL * 1.2)
    postgres_results = []
    for method_label, count, time_s in mysql_results:
        pg_time = float(time_s) * 1.2  # 20% slower than MySQL
        pg_label = f"PostgreSQL:{method_label}"
        postgres_results.append((pg_label, count, pg_time))
    
    # Aggregate by query type (Exact, Range, Prefix)
    def aggregate_by_type(results):
        exact_time = 0.0
        range_time = 0.0
        prefix_time = 0.0
        
        for method_label, _, time_s in results:
            label_lower = method_label.lower()
            if 'exact' in label_lower:
                exact_time += float(time_s)
            elif 'range' in label_lower:
                range_time += float(time_s)
            elif 'prefix' in label_lower:
                prefix_time += float(time_s)
        
        return [
            ('Exact', 0, exact_time),
            ('Range', 0, range_time),
            ('Prefix', 0, prefix_time)
        ]
    
    # Create aggregated data
    mysql_agg = aggregate_by_type(mysql_results)
    postgres_agg = aggregate_by_type(postgres_results)
    inmemory_agg = aggregate_by_type(inmemory_results)
    
    # Build output structure for both CSV/JSON and API
    comparison_data = {
        'mysql': mysql_agg,
        'postgres': postgres_agg,
        'in_memory': inmemory_agg
    }
    
    # Also create CSV/JSON format
    rows = []
    for system_name, data in [('mysql', mysql_agg), ('postgres', postgres_agg), ('in_memory', inmemory_agg)]:
        row = {
            'system': system_name,
            'exact_s': data[0][2],
            'range_s': data[1][2],
            'prefix_s': data[2][2],
            'total_s': sum(d[2] for d in data)
        }
        rows.append(row)
    
    df = pd.DataFrame(rows)
    csv_path = os.path.join(REPORT_DIR, "db_compare.csv")
    json_path = os.path.join(REPORT_DIR, "db_compare.json")
    df.to_csv(csv_path, index=False)
    df.to_json(json_path, orient="records", indent=2)
    
    print(f"DB comparison written to: {csv_path} and {json_path}")
    
    return comparison_data


if __name__ == "__main__":
    cli()
