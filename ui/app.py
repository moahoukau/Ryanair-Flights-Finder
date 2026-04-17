import threading
import queue
from datetime import date
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from models.trip_result import TripResult
from models.search_config import SearchConfig
from services.csv_service import save_results_to_csv
from services.ryanair_service import search_trips


class App(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Ryanair Trip Finder")
        self.geometry("1200x700")
        self.minsize(1000, 600)

        self.results: list[TripResult] = []
        self.worker_thread: threading.Thread | None = None
        self.ui_queue: queue.Queue = queue.Queue()

        self._build_ui()
        self.after(200, self._process_queue)

    def _build_ui(self):
        root = ttk.Frame(self, padding=12)
        root.pack(fill="both", expand=True)

        form = ttk.LabelFrame(root, text="Search settings", padding=10)
        form.pack(fill="x", padx=5, pady=5)

        ttk.Label(form, text="Origin:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.origin_var = tk.StringVar(value="BTS")
        ttk.Entry(form, textvariable=self.origin_var, width=12).grid(row=0, column=1, sticky="w", padx=5, pady=5)

        ttk.Label(form, text="Window start (YYYY-MM-DD):").grid(row=0, column=2, sticky="w", padx=5, pady=5)
        self.start_var = tk.StringVar(value="2026-06-23")
        ttk.Entry(form, textvariable=self.start_var, width=15).grid(row=0, column=3, sticky="w", padx=5, pady=5)

        ttk.Label(form, text="Window end (YYYY-MM-DD):").grid(row=0, column=4, sticky="w", padx=5, pady=5)
        self.end_var = tk.StringVar(value="2026-07-10")
        ttk.Entry(form, textvariable=self.end_var, width=15).grid(row=0, column=5, sticky="w", padx=5, pady=5)

        ttk.Label(form, text="Min nights:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.min_nights_var = tk.StringVar(value="8")
        ttk.Spinbox(form, from_=1, to=30, textvariable=self.min_nights_var, width=10).grid(
            row=1, column=1, sticky="w", padx=5, pady=5
        )

        ttk.Label(form, text="Max nights:").grid(row=1, column=2, sticky="w", padx=5, pady=5)
        self.max_nights_var = tk.StringVar(value="10")
        ttk.Spinbox(form, from_=1, to=30, textvariable=self.max_nights_var, width=10).grid(
            row=1, column=3, sticky="w", padx=5, pady=5
        )

        ttk.Label(form, text="Destinations:").grid(row=1, column=4, sticky="w", padx=5, pady=5)
        self.destination_mode_var = tk.StringVar(value="all")
        ttk.Radiobutton(form, text="All from API", variable=self.destination_mode_var, value="all").grid(
            row=1, column=5, sticky="w", padx=5, pady=5
        )
        ttk.Radiobutton(form, text="Sea only", variable=self.destination_mode_var, value="sea").grid(
            row=1, column=6, sticky="w", padx=5, pady=5
        )

        buttons = ttk.Frame(root)
        buttons.pack(fill="x", padx=5, pady=5)

        self.search_btn = ttk.Button(buttons, text="Search", command=self._on_search)
        self.search_btn.pack(side="left", padx=5)

        self.save_btn = ttk.Button(buttons, text="Save CSV", command=self._on_save, state="disabled")
        self.save_btn.pack(side="left", padx=5)

        self.clear_btn = ttk.Button(buttons, text="Clear", command=self._on_clear)
        self.clear_btn.pack(side="left", padx=5)

        results_frame = ttk.LabelFrame(root, text="Results", padding=8)
        results_frame.pack(fill="both", expand=True, padx=5, pady=5)

        columns = (
            "destination",
            "airport",
            "departure_date",
            "return_date",
            "nights",
            "total_price_eur",
            "outbound_flight",
            "inbound_flight",
            "outbound_departure",
            "inbound_departure",
        )

        self.tree = ttk.Treeview(results_frame, columns=columns, show="headings")
        self.tree.pack(side="left", fill="both", expand=True)

        headings = {
            "destination": "Destination",
            "airport": "Airport",
            "departure_date": "Departure",
            "return_date": "Return",
            "nights": "Nights",
            "total_price_eur": "Price EUR",
            "outbound_flight": "Outbound flight",
            "inbound_flight": "Inbound flight",
            "outbound_departure": "Outbound departure",
            "inbound_departure": "Inbound departure",
        }

        widths = {
            "destination": 180,
            "airport": 70,
            "departure_date": 100,
            "return_date": 100,
            "nights": 70,
            "total_price_eur": 90,
            "outbound_flight": 110,
            "inbound_flight": 110,
            "outbound_departure": 170,
            "inbound_departure": 170,
        }

        for col in columns:
            self.tree.heading(col, text=headings[col])
            self.tree.column(col, width=widths[col], anchor="center")

        scrollbar_y = ttk.Scrollbar(results_frame, orient="vertical", command=self.tree.yview)
        scrollbar_y.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scrollbar_y.set)

        self.status_var = tk.StringVar(value="Ready.")
        status_bar = ttk.Label(root, textvariable=self.status_var, relief="sunken", anchor="w")
        status_bar.pack(fill="x", padx=5, pady=5)

    def _read_config(self) -> SearchConfig:
        origin = self.origin_var.get().strip().upper()
        start = date.fromisoformat(self.start_var.get().strip())
        end = date.fromisoformat(self.end_var.get().strip())
        min_nights = int(self.min_nights_var.get())
        max_nights = int(self.max_nights_var.get())
        destination_mode = self.destination_mode_var.get().strip()

        if not origin:
            raise ValueError("Origin is empty.")
        if start > end:
            raise ValueError("Window start must be before or equal to window end.")
        if min_nights < 1 or max_nights < 1:
            raise ValueError("Nights must be positive.")
        if min_nights > max_nights:
            raise ValueError("Min nights cannot be greater than max nights.")
        if destination_mode not in {"all", "sea"}:
            raise ValueError("Destination mode must be 'all' or 'sea'.")

        return SearchConfig(
            origin=origin,
            window_start=start,
            window_end=end,
            min_nights=min_nights,
            max_nights=max_nights,
            destination_mode=destination_mode,
            currency="EUR",
        )

    def _on_search(self):
        if self.worker_thread and self.worker_thread.is_alive():
            messagebox.showinfo("Search in progress", "Search is already running.")
            return

        try:
            config = self._read_config()
        except Exception as e:
            messagebox.showerror("Invalid input", str(e))
            return

        self._clear_table()
        self.results = []
        self.save_btn.config(state="disabled")
        self.search_btn.config(state="disabled")
        self._set_status("Starting search...")

        self.worker_thread = threading.Thread(
            target=self._search_worker,
            args=(config,),
            daemon=True,
        )
        self.worker_thread.start()

    def _search_worker(self, config: SearchConfig):
        try:
            results = search_trips(
                config,
                progress_callback=lambda text: self.ui_queue.put(("status", text)),
            )
            self.ui_queue.put(("done", results))
        except Exception as e:
            self.ui_queue.put(("error", str(e)))

    def _process_queue(self):
        try:
            while True:
                kind, payload = self.ui_queue.get_nowait()

                if kind == "status":
                    self._set_status(payload)

                elif kind == "done":
                    self.results = payload
                    self._fill_table(payload)
                    self.search_btn.config(state="normal")
                    self.save_btn.config(state="normal" if payload else "disabled")
                    self._set_status(f"Finished. Found {len(payload)} options.")

                elif kind == "error":
                    self.search_btn.config(state="normal")
                    self.save_btn.config(state="disabled")
                    self._set_status("Error.")
                    messagebox.showerror("Search error", payload)

        except queue.Empty:
            pass
        finally:
            self.after(200, self._process_queue)

    def _fill_table(self, results: list[TripResult]):
        for row in results:
            self.tree.insert(
                "",
                "end",
                values=(
                    row.destination,
                    row.airport,
                    row.departure_date,
                    row.return_date,
                    row.nights,
                    f"{row.total_price_eur:.2f}",
                    row.outbound_flight,
                    row.inbound_flight,
                    row.outbound_departure,
                    row.inbound_departure,
                ),
            )

    def _clear_table(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

    def _on_clear(self):
        if self.worker_thread and self.worker_thread.is_alive():
            messagebox.showinfo("Busy", "Search is still running.")
            return

        self._clear_table()
        self.results = []
        self.save_btn.config(state="disabled")
        self._set_status("Cleared.")

    def _on_save(self):
        if not self.results:
            messagebox.showinfo("No data", "There are no results to save.")
            return

        filename = filedialog.asksaveasfilename(
            title="Save CSV",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfile="ryanair_results.csv",
        )

        if not filename:
            return

        try:
            save_results_to_csv(self.results, filename)
            self._set_status(f"Saved to {filename}")
            messagebox.showinfo("Saved", f"CSV saved:\n{filename}")
        except Exception as e:
            messagebox.showerror("Save error", str(e))

    def _set_status(self, text: str):
        self.status_var.set(text)