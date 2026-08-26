"""
Scoops and Smiles — Tkinter GUI Application
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from datetime import date
import calendar as _cal

import database
import logic
import reports
import validation

# ── colour palette ────────────────────────────────────────────────────────────
BG        = "#FFF6F9"
HEADER_BG = "#E8557A"
HEADER_FG = "#000000"
BTN_BG    = "#E8557A"
BTN_FG    = "#000000"
BTN_HOV   = "#C9425F"
LABEL_FG  = "#000000"
ENTRY_FG  = "#000000"
ENTRY_BG  = "#FFFFFF"
SEP_COLOR = "#F2C4D0"

FONT_TITLE  = ("Helvetica", 18, "bold")
FONT_HEADER = ("Helvetica", 14, "bold")
FONT_BODY   = ("Helvetica", 12)
FONT_BTN    = ("Helvetica", 12, "bold")
FONT_MONO   = ("Courier", 11)
FONT_LOC    = ("Helvetica", 13, "bold")

MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


# ── small helpers ─────────────────────────────────────────────────────────────

def _label(parent, text, font=FONT_BODY, fg=LABEL_FG, **kw):
    return tk.Label(parent, text=text, font=font, fg=fg, bg=BG, **kw)


def _entry(parent, width=14, default=""):
    e = tk.Entry(parent, font=FONT_BODY, width=width,
                 bg=ENTRY_BG, fg=ENTRY_FG,
                 insertbackground=ENTRY_FG, relief="solid", bd=1)
    if default:
        e.insert(0, default)
    return e


def _btn(parent, text, command, width=22, pady=6):
    b = tk.Button(parent, text=text, command=command, font=FONT_BTN,
                  bg=BTN_BG, fg=BTN_FG, activebackground=BTN_HOV,
                  activeforeground=BTN_FG, relief="flat",
                  cursor="hand2", width=width, pady=pady)
    return b


def _center(win, w, h):
    """Center a Toplevel on screen."""
    win.update_idletasks()
    sw = win.winfo_screenwidth()
    sh = win.winfo_screenheight()
    win.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")


def _loc_banner(parent, location_name):
    return tk.Label(parent, text=f"Location: {location_name}",
                    font=FONT_LOC, bg=SEP_COLOR, fg=LABEL_FG,
                    pady=6, padx=10, anchor="center")


class DateDropdowns(tk.Frame):
    """Year / Month / Day combo-box date picker (no tkcalendar dependency)."""

    def __init__(self, parent, **kw):
        super().__init__(parent, bg=BG, **kw)
        today = date.today()

        # Month
        self._month_var = tk.StringVar(value=MONTH_NAMES[today.month - 1])
        self._month_cb = ttk.Combobox(
            self, textvariable=self._month_var, values=MONTH_NAMES,
            font=FONT_BODY, state="readonly", width=10,
        )
        self._month_cb.pack(side="left", padx=(0, 4))

        # Day
        self._day_var = tk.StringVar(value=str(today.day))
        self._day_cb = ttk.Combobox(
            self, textvariable=self._day_var,
            font=FONT_BODY, state="readonly", width=4,
        )
        self._day_cb.pack(side="left", padx=(0, 4))

        # Year
        years = [str(y) for y in range(today.year - 5, today.year + 1)]
        self._year_var = tk.StringVar(value=str(today.year))
        self._year_cb = ttk.Combobox(
            self, textvariable=self._year_var, values=years,
            font=FONT_BODY, state="readonly", width=6,
        )
        self._year_cb.pack(side="left")

        # Refresh day list whenever month/year changes
        self._month_var.trace_add("write", self._refresh_days)
        self._year_var.trace_add("write", self._refresh_days)
        self._refresh_days()

    def _refresh_days(self, *_):
        try:
            m = MONTH_NAMES.index(self._month_var.get()) + 1
            y = int(self._year_var.get())
        except (ValueError, IndexError):
            return
        max_day = _cal.monthrange(y, m)[1]
        days = [str(d) for d in range(1, max_day + 1)]
        self._day_cb["values"] = days
        if self._day_var.get() not in days:
            self._day_var.set(days[-1])

    def get_date(self) -> date:
        m = MONTH_NAMES.index(self._month_var.get()) + 1
        y = int(self._year_var.get())
        d = int(self._day_var.get())
        return date(y, m, d)


def _date_entry(parent):
    """Drop-in replacement that returns a DateDropdowns frame."""
    return DateDropdowns(parent)


def _display_text(widget, text):
    """Replace all text in a scrolledtext widget."""
    widget.config(state="normal")
    widget.delete("1.0", "end")
    widget.insert("end", text)
    widget.config(state="disabled")


# ── main application ──────────────────────────────────────────────────────────

class ScoopsApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Scoops & Smiles Management System")
        self.root.configure(bg=BG)
        self.root.resizable(False, False)

        self.locations  = database.get_locations()   # [{'location_id', 'location_name'}]
        self.flavors    = database.get_flavors()     # [{'flavor_id', 'flavor_name', ...}]
        self.containers = database.get_containers()  # [{'container_id', 'container_name', ...}]

        self._loc_name_to_id  = {loc["location_name"]: loc["location_id"] for loc in self.locations}
        self._flav_name_to_id = {f["flavor_name"]:     f["flavor_id"]     for f in self.flavors}
        self._flav_id_to_cost = {f["flavor_id"]:       f["cost_per_container"] for f in self.flavors}
        self._cont_name_to_id = {c["container_name"]:  c["container_id"]  for c in self.containers}
        self._cont_id_to_cost = {c["container_id"]:    c["cost_per_100"]  for c in self.containers}

        self.location_var = tk.StringVar(value=self.locations[0]["location_name"])

        self._apply_styles()
        self._build()
        _center(root, 380, 550)

    def _apply_styles(self):
        style = ttk.Style()
        try:
            style.theme_use("default")
        except Exception:
            pass
        style.configure(".",          foreground="#000000", background=BG)
        style.configure("TButton",    foreground="#000000")
        style.configure("TLabel",     foreground="#000000", background=BG)
        style.configure("TEntry",     foreground="#000000", fieldbackground="white")
        style.configure("TCombobox",  foreground="#000000", fieldbackground="white")
        style.configure("TScrollbar", troughcolor=SEP_COLOR)
        style.configure("TNotebook",  background=BG)
        style.configure("TNotebook.Tab", background=SEP_COLOR, foreground="#000000",
                        padding=[10, 4])
        style.map("TNotebook.Tab",
                  background=[("selected", HEADER_BG)],
                  foreground=[("selected", "#000000")])

    # ── helpers ───────────────────────────────────────────────────────────────

    def _loc_id(self):
        return self._loc_name_to_id[self.location_var.get()]

    def _loc_name(self):
        return self.location_var.get()

    # ── main window ───────────────────────────────────────────────────────────

    def _build(self):
        hdr = tk.Frame(self.root, bg=HEADER_BG, pady=14)
        hdr.pack(fill="x")
        tk.Label(hdr, text="Scoops & Smiles",
                 font=FONT_TITLE, bg=HEADER_BG, fg=HEADER_FG).pack()
        tk.Label(hdr, text="Management System",
                 font=("Helvetica", 12), bg=HEADER_BG, fg="#000000").pack()

        loc_frame = tk.Frame(self.root, bg=SEP_COLOR, pady=8)
        loc_frame.pack(fill="x")
        tk.Label(loc_frame, text="Current Location:", font=FONT_BODY,
                 bg=SEP_COLOR, fg=LABEL_FG).pack(side="left", padx=(15, 6))
        loc_names = [loc["location_name"] for loc in self.locations]
        om = tk.OptionMenu(loc_frame, self.location_var, *loc_names)
        om.config(font=FONT_BODY, bg=ENTRY_BG, fg=ENTRY_FG,
                  relief="solid", bd=1, highlightthickness=0, width=18)
        om["menu"].config(font=FONT_BODY, bg=ENTRY_BG, fg=ENTRY_FG)
        om.pack(side="left")

        btn_frame = tk.Frame(self.root, bg=BG, pady=20)
        btn_frame.pack(fill="both", expand=True, padx=40)

        actions = [
            ("View Current Inventory",  self._open_inventory),
            ("Purchase Inventory",      self._open_purchase),
            ("Record Sales",            self._open_sales),
            ("View Reports",            self._open_reports),
            ("Exit",                    self.root.destroy),
        ]
        for text, cmd in actions:
            _btn(btn_frame, text, cmd).pack(pady=7, fill="x")

    # ── view current inventory ────────────────────────────────────────────────

    def _open_inventory(self):
        win = tk.Toplevel(self.root)
        win.title("Current Inventory")
        win.configure(bg=BG)
        win.resizable(True, True)
        win.grab_set()
        _center(win, 560, 620)

        loc_name = self._loc_name()
        loc_id   = self._loc_id()

        # Header
        tk.Label(win, text=f"Current Inventory — {loc_name}",
                 font=FONT_HEADER, bg=BG, fg="#000000").pack(pady=(16, 4))

        try:
            inv = logic.get_current_inventory(loc_id)
        except Exception as exc:
            tk.Label(win, text=f"Error loading inventory:\n{exc}",
                     font=FONT_BODY, bg=BG, fg="red").pack(pady=20)
            _btn(win, "Close", win.destroy, width=12).pack(pady=8)
            return

        # Summary line
        flavs = inv["flavors"]
        conts = inv["containers"]
        nap   = inv["napkins"]

        all_items = (
            [f["status"] for f in flavs]
            + [c["status"] for c in conts]
            + [nap["status"]]
        )
        n_crit = all_items.count("critical")
        n_low  = all_items.count("low")
        n_ok   = all_items.count("ok")

        summary_frame = tk.Frame(win, bg=SEP_COLOR, pady=6)
        summary_frame.pack(fill="x", padx=20, pady=(0, 8))
        tk.Label(summary_frame,
                 text=f"  Critical: {n_crit}   |   Low: {n_low}   |   OK: {n_ok}",
                 font=FONT_BODY, bg=SEP_COLOR, fg=LABEL_FG).pack()

        # Scrollable content frame
        outer = tk.Frame(win, bg=BG)
        outer.pack(fill="both", expand=True, padx=15, pady=(0, 8))

        canvas = tk.Canvas(outer, bg=BG, highlightthickness=0)
        vsb    = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        inner  = tk.Frame(canvas, bg=BG)
        inner.bind("<Configure>",
                   lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=vsb.set)
        canvas.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        def _bind_scroll(widget):
            widget.bind("<MouseWheel>",
                        lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))
            for child in widget.winfo_children():
                _bind_scroll(child)

        STATUS_COLOR = {"critical": "#FFCCCC", "low": "#FFF3CC", "ok": "#CCFFCC"}

        def _section_header(text):
            tk.Label(inner, text=text, font=("Helvetica", 12, "bold"),
                     bg=SEP_COLOR, fg=LABEL_FG, anchor="w", padx=8, pady=4
                     ).pack(fill="x", pady=(10, 2))

        def _row_frame(status, cols):
            """Pack a data row with background color based on status."""
            bg_color = STATUS_COLOR.get(status, BG)
            rf = tk.Frame(inner, bg=bg_color)
            rf.pack(fill="x", padx=4, pady=1)
            for text, width, anchor in cols:
                tk.Label(rf, text=text, font=FONT_BODY, bg=bg_color, fg=LABEL_FG,
                         width=width, anchor=anchor).pack(side="left", padx=4)

        # Flavors section
        _section_header("FLAVORS")
        # Column headers
        hf = tk.Frame(inner, bg=SEP_COLOR)
        hf.pack(fill="x", padx=4)
        for txt, w in [("Flavor", 18), ("Oz on Hand", 12), ("Equiv. Containers", 17), ("Status", 10)]:
            tk.Label(hf, text=txt, font=("Helvetica", 11, "bold"),
                     bg=SEP_COLOR, fg=LABEL_FG, width=w, anchor="w"
                     ).pack(side="left", padx=4)

        for f in flavs:
            equiv = f["quantity_oz"] / 640
            status_disp = f["status"].upper()
            _row_frame(f["status"], [
                (f["flavor_name"],          18, "w"),
                (f"{f['quantity_oz']:,.0f}", 12, "e"),
                (f"{equiv:.1f}",             17, "e"),
                (status_disp,                10, "w"),
            ])

        # Containers section
        _section_header("CONTAINERS")
        hc = tk.Frame(inner, bg=SEP_COLOR)
        hc.pack(fill="x", padx=4)
        for txt, w in [("Container Type", 22), ("Units on Hand", 14), ("Status", 10)]:
            tk.Label(hc, text=txt, font=("Helvetica", 11, "bold"),
                     bg=SEP_COLOR, fg=LABEL_FG, width=w, anchor="w"
                     ).pack(side="left", padx=4)

        for c in conts:
            status_disp = c["status"].upper()
            _row_frame(c["status"], [
                (c["container_name"],           22, "w"),
                (f"{c['quantity_units']:,}",    14, "e"),
                (status_disp,                    10, "w"),
            ])

        # Napkins section
        _section_header("NAPKINS")
        hn = tk.Frame(inner, bg=SEP_COLOR)
        hn.pack(fill="x", padx=4)
        for txt, w in [("Item", 22), ("Units on Hand", 14), ("Status", 10)]:
            tk.Label(hn, text=txt, font=("Helvetica", 11, "bold"),
                     bg=SEP_COLOR, fg=LABEL_FG, width=w, anchor="w"
                     ).pack(side="left", padx=4)

        _row_frame(nap["status"], [
            ("Napkins",                  22, "w"),
            (f"{nap['quantity']:,}",     14, "e"),
            (nap["status"].upper(),      10, "w"),
        ])

        _bind_scroll(inner)
        win.bind("<MouseWheel>",
                 lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

        _btn(win, "Close", win.destroy, width=12).pack(pady=10)

    # ── purchase inventory ────────────────────────────────────────────────────

    def _open_purchase(self):
        win = tk.Toplevel(self.root)
        win.title("Purchase Inventory")
        win.configure(bg=BG)
        win.resizable(False, False)
        win.grab_set()
        _center(win, 500, 520)

        loc_name = self._loc_name()
        loc_id   = self._loc_id()

        tk.Label(win, text="Purchase Inventory", font=FONT_HEADER,
                 bg=BG, fg="#000000").pack(pady=(18, 4))
        _loc_banner(win, loc_name).pack(fill="x", padx=20, pady=(0, 10))

        fields = tk.Frame(win, bg=BG)
        fields.pack(padx=30, fill="x")
        fields.columnconfigure(1, weight=1)

        row = [0]  # mutable counter for grid rows

        def next_row():
            r = row[0]
            row[0] += 1
            return r

        # Item Type
        _label(fields, "Item Type:").grid(row=next_row(), column=0, sticky="w",
                                          padx=10, pady=6)
        type_var = tk.StringVar(value="Flavor")
        type_row = next_row() - 1  # stays on same row as label
        type_frame = tk.Frame(fields, bg=BG)
        type_frame.grid(row=type_row, column=1, sticky="ew", padx=10, pady=6)
        for t in ("Flavor", "Container", "Napkins"):
            tk.Radiobutton(type_frame, text=t, variable=type_var, value=t,
                           font=FONT_BODY, bg=BG, fg=LABEL_FG,
                           selectcolor=BG, activebackground=BG,
                           command=lambda: _on_type_change()).pack(side="left", padx=4)

        # Item Name
        item_label = _label(fields, "Item Name:")
        item_label.grid(row=next_row(), column=0, sticky="w", padx=10, pady=6)
        item_row = row[0] - 1

        flavor_names    = [f["flavor_name"]    for f in self.flavors]
        container_names = [c["container_name"] for c in self.containers]

        item_var = tk.StringVar(value=flavor_names[0])
        item_cb  = ttk.Combobox(fields, textvariable=item_var, font=FONT_BODY,
                                 state="readonly", width=22)
        item_cb["values"] = flavor_names
        item_cb.grid(row=item_row, column=1, sticky="ew", padx=10, pady=6)

        # Quantity
        qty_label = _label(fields, "# of containers:")
        qty_label.grid(row=next_row(), column=0, sticky="w", padx=10, pady=6)
        qty_row = row[0] - 1
        qty_e = _entry(fields)
        qty_e.grid(row=qty_row, column=1, sticky="ew", padx=10, pady=6)

        # Estimated Cost
        cost_label = _label(fields, "Estimated Cost:")
        cost_label.grid(row=next_row(), column=0, sticky="w", padx=10, pady=6)
        cost_row = row[0] - 1
        cost_var = tk.StringVar(value="$0.00")
        tk.Label(fields, textvariable=cost_var, font=FONT_BODY,
                 bg=BG, fg="#333333", anchor="w").grid(
            row=cost_row, column=1, sticky="ew", padx=10, pady=6)

        # Purchase Date
        date_label_w = _label(fields, "Purchase Date:")
        date_label_w.grid(row=next_row(), column=0, sticky="w", padx=10, pady=6)
        date_row = row[0] - 1
        date_entry = _date_entry(fields)
        date_entry.grid(row=date_row, column=1, sticky="ew", padx=10, pady=6)

        # ── cost calculation ──────────────────────────────────────────────────
        def _calc_cost(*_):
            try:
                qty = int(qty_e.get())
                if qty <= 0:
                    raise ValueError
            except (ValueError, TypeError):
                cost_var.set("$0.00")
                return

            t = type_var.get()
            if t == "Flavor":
                flavor_id = self._flav_name_to_id.get(item_var.get())
                if flavor_id:
                    unit_cost  = self._flav_id_to_cost[flavor_id]
                    total_cost = qty * unit_cost
                    cost_var.set(
                        f"${total_cost:.2f}  ({qty} container(s) × ${unit_cost:.2f})"
                        f"  —  {qty * 640:,} oz total  ({qty} × 640 oz)"
                    )
                else:
                    cost_var.set("$0.00")
            elif t == "Container":
                cont_id = self._cont_name_to_id.get(item_var.get())
                if cont_id:
                    unit_cost  = self._cont_id_to_cost[cont_id]
                    total_cost = qty * unit_cost
                    cost_var.set(
                        f"${total_cost:.2f}  ({qty} pack(s) × ${unit_cost:.2f})"
                        f"  —  {qty * 100:,} units total  ({qty} × 100)"
                    )
                else:
                    cost_var.set("$0.00")
            else:  # Napkins
                total_cost = qty * 20.00
                cost_var.set(
                    f"${total_cost:.2f}  ({qty} pack(s) × $20.00)"
                    f"  —  {qty * 10000:,} napkins total  ({qty} × 10,000)"
                )

        qty_e.bind("<KeyRelease>", _calc_cost)
        item_var.trace_add("write", _calc_cost)

        def _on_type_change(*_):
            t = type_var.get()
            if t == "Flavor":
                item_cb["values"] = flavor_names
                item_var.set(flavor_names[0])
                item_label.config(text="Item Name:")
                qty_label.config(text="# of containers:")
                item_cb.grid()
            elif t == "Container":
                item_cb["values"] = container_names
                item_var.set(container_names[0])
                item_label.config(text="Item Name:")
                qty_label.config(text="# of 100-packs:")
                item_cb.grid()
            else:  # Napkins
                item_cb["values"] = ["Napkins"]
                item_var.set("Napkins")
                item_label.config(text="Item Name:")
                qty_label.config(text="# of 10,000-packs:")
                item_cb.grid()
            _calc_cost()

        # ── submit ────────────────────────────────────────────────────────────
        def submit():
            try:
                ok, err = validation.validate_positive_integer(qty_e.get(), "Quantity")
                if not ok:
                    messagebox.showerror("Validation Error", err, parent=win)
                    return

                try:
                    chosen_date = date_entry.get_date()
                except Exception as e:
                    messagebox.showerror("Date Error", f"Invalid date: {e}", parent=win)
                    return

                if chosen_date > date.today():
                    messagebox.showerror("Validation Error",
                                         "Purchase date cannot be in the future.", parent=win)
                    return

                qty = int(qty_e.get())
                t   = type_var.get()

                if t == "Flavor":
                    flavor_id = self._flav_name_to_id[item_var.get()]
                    logic.purchase_flavor(loc_id, flavor_id, qty, chosen_date)
                    messagebox.showinfo("Success",
                        f"Purchased {qty} container(s) of {item_var.get()}.", parent=win)
                elif t == "Container":
                    cont_id = self._cont_name_to_id[item_var.get()]
                    logic.purchase_containers(loc_id, cont_id, qty, chosen_date)
                    messagebox.showinfo("Success",
                        f"Purchased {qty} 100-pack(s) of {item_var.get()}.", parent=win)
                else:  # Napkins
                    logic.purchase_napkins(loc_id, qty, chosen_date)
                    messagebox.showinfo("Success",
                        f"Purchased {qty} × 10,000-pack(s) of napkins.", parent=win)
                win.destroy()
            except Exception as e:
                import traceback
                traceback.print_exc()
                messagebox.showerror("Purchase Failed", f"Error: {str(e)}", parent=win)

        btn_row = tk.Frame(win, bg=BG)
        btn_row.pack(pady=(12, 18))
        _btn(btn_row, "Submit", submit, width=14).pack(side="left", padx=6)
        _btn(btn_row, "Cancel", win.destroy, width=14).pack(side="left", padx=6)

    # ── record sales ──────────────────────────────────────────────────────────

    def _open_sales(self):
        win = tk.Toplevel(self.root)
        win.title("Record Sales")
        win.configure(bg=BG)
        win.resizable(False, False)
        win.focus_set()
        _center(win, 480, 550)

        loc_name = self._loc_name()
        loc_id   = self._loc_id()

        tk.Label(win, text="Record Sales", font=FONT_HEADER,
                 bg=BG, fg="#000000").pack(pady=(18, 4))
        _loc_banner(win, loc_name).pack(fill="x", padx=20, pady=(0, 10))

        fields = tk.Frame(win, bg=BG)
        fields.pack(padx=30, fill="x")
        fields.columnconfigure(1, weight=1)

        SIZE_LABELS = {
            "Kiddie": "Kiddie  ($3.00 — 1 scoop, 4 oz)",
            "Small":  "Small   ($3.50 — 2 scoops, 8 oz)",
            "Medium": "Medium  ($4.00 — 3 scoops, 12 oz)",
            "Large":  "Large   ($4.50 — 4 scoops, 16 oz)",
        }

        # Flavor
        _label(fields, "Flavor:").grid(row=0, column=0, sticky="w", padx=10, pady=6)
        flavor_var = tk.StringVar(value=self.flavors[0]["flavor_name"])
        flavor_names = [f["flavor_name"] for f in self.flavors]
        flavor_cb = ttk.Combobox(fields, textvariable=flavor_var,
                                  values=flavor_names, font=FONT_BODY,
                                  state="readonly", width=22)
        flavor_cb.grid(row=0, column=1, sticky="ew", padx=10, pady=6)

        # Size
        _label(fields, "Size:").grid(row=1, column=0, sticky="w", padx=10, pady=6)
        size_labels_list = list(SIZE_LABELS.values())
        size_keys = list(SIZE_LABELS.keys())
        size_cb = ttk.Combobox(fields, values=size_labels_list, font=FONT_BODY,
                                state="readonly", width=28)
        size_cb.current(1)  # default "Small"
        size_cb.grid(row=1, column=1, sticky="ew", padx=10, pady=6)

        # Container
        _label(fields, "Container:").grid(row=2, column=0, sticky="w", padx=10, pady=6)
        cont_var = tk.StringVar(value=self.containers[0]["container_name"])
        cont_names = [c["container_name"] for c in self.containers]
        cont_cb = ttk.Combobox(fields, textvariable=cont_var,
                                values=cont_names, font=FONT_BODY,
                                state="readonly", width=22)
        cont_cb.grid(row=2, column=1, sticky="ew", padx=10, pady=6)

        # Quantity
        _label(fields, "Quantity:").grid(row=3, column=0, sticky="w", padx=10, pady=6)
        qty_var = tk.IntVar(value=1)
        qty_spin = tk.Spinbox(fields, from_=1, to=999, textvariable=qty_var,
                              font=FONT_BODY, width=6)
        qty_spin.grid(row=3, column=1, sticky="w", padx=10, pady=6)

        # Sale Date
        _label(fields, "Sale Date:").grid(row=4, column=0, sticky="w", padx=10, pady=6)
        sale_date_entry = _date_entry(fields)
        sale_date_entry.grid(row=4, column=1, sticky="ew", padx=10, pady=6)

        # Total Price (auto-calculated)
        _label(fields, "Total Price:").grid(row=5, column=0, sticky="w", padx=10, pady=6)
        price_var = tk.StringVar(value="$3.50")
        tk.Label(fields, textvariable=price_var, font=("Helvetica", 13, "bold"),
                 bg=BG, fg="#1a7a1a", anchor="w").grid(
            row=5, column=1, sticky="ew", padx=10, pady=6)

        def _update_price(*_):
            idx = size_cb.current()
            if 0 <= idx < len(size_keys):
                key = size_keys[idx]
                p   = logic.SIZE_MAP[key]['price']
                try:
                    qty = int(qty_var.get())
                except (ValueError, tk.TclError):
                    qty = 1
                price_var.set(f"${p * qty:.2f}")

        size_cb.bind("<<ComboboxSelected>>", _update_price)
        qty_var.trace_add("write", _update_price)
        _update_price()

        # ── submit ────────────────────────────────────────────────────────────
        def submit():
            idx = size_cb.current()
            if idx < 0:
                messagebox.showerror("Validation Error", "Please select a size.", parent=win)
                return
            try:
                qty = int(qty_var.get())
                if qty < 1:
                    raise ValueError
            except (ValueError, tk.TclError):
                messagebox.showerror("Validation Error", "Quantity must be a whole number ≥ 1.", parent=win)
                return

            size_key   = size_keys[idx]
            flavor_id  = self._flav_name_to_id.get(flavor_var.get())
            cont_id    = self._cont_name_to_id.get(cont_var.get())
            chosen_date = sale_date_entry.get_date()

            if chosen_date > date.today():
                messagebox.showerror("Validation Error",
                                     "Sale date cannot be in the future.", parent=win)
                return

            try:
                total = logic.record_sale(loc_id, flavor_id, cont_id, size_key, chosen_date, qty)
                messagebox.showinfo("Sale Recorded",
                    f"{qty}x {size_key} {flavor_var.get()} in {cont_var.get()}\n"
                    f"Total: ${total:.2f}", parent=win)
                win.destroy()
            except ValueError as exc:
                messagebox.showerror("Insufficient Stock", str(exc), parent=win)
            except Exception as exc:
                messagebox.showerror("Error", str(exc), parent=win)

        btn_row = tk.Frame(win, bg=BG)
        btn_row.pack(pady=(14, 18))
        _btn(btn_row, "Submit", submit, width=14).pack(side="left", padx=6)
        _btn(btn_row, "Cancel", win.destroy, width=14).pack(side="left", padx=6)

    # ── view reports ──────────────────────────────────────────────────────────

    def _open_reports(self):
        win = tk.Toplevel(self.root)
        win.title("Reports")
        win.configure(bg=BG)
        win.resizable(True, True)
        win.focus_set()
        _center(win, 740, 660)

        tk.Label(win, text="Reports", font=FONT_HEADER,
                 bg=BG, fg="#000000").pack(pady=(14, 4))

        notebook = ttk.Notebook(win)
        notebook.pack(fill="both", expand=True, padx=15, pady=(0, 12))

        loc_names_with_all = ["All Locations"] + [l["location_name"] for l in self.locations]
        loc_names_only     = [l["location_name"] for l in self.locations]

        # ── helper: shared output widget ─────────────────────────────────────
        def _make_output(parent):
            out = scrolledtext.ScrolledText(
                parent, font=FONT_MONO, wrap="none",
                bg="#FFFFFF", fg="#000000", width=82, height=22,
                state="disabled", relief="solid", bd=1,
            )
            out.pack(padx=10, pady=(4, 8), fill="both", expand=True)
            return out

        # ── Tab 1: Monthly Income Statement ──────────────────────────────────
        tab1 = tk.Frame(notebook, bg=BG)
        notebook.add(tab1, text="Monthly Income Statement")

        ctrl1 = tk.Frame(tab1, bg=BG)
        ctrl1.pack(pady=(10, 4))

        tk.Label(ctrl1, text="Month:", font=FONT_BODY, bg=BG).grid(
            row=0, column=0, padx=6, pady=4, sticky="e")
        # Default to last completed month
        _today = date.today()
        _def_month = _today.month - 1 if _today.month > 1 else 12
        _def_year  = _today.year if _today.month > 1 else _today.year - 1
        month_var = tk.StringVar(value=MONTH_NAMES[_def_month - 1])
        month_cb  = ttk.Combobox(ctrl1, textvariable=month_var, values=MONTH_NAMES,
                                  font=FONT_BODY, state="readonly", width=12)
        month_cb.grid(row=0, column=1, padx=6, pady=4)

        tk.Label(ctrl1, text="Year:", font=FONT_BODY, bg=BG).grid(
            row=0, column=2, padx=6, pady=4, sticky="e")
        year_e1 = _entry(ctrl1, width=7, default=str(_def_year))
        year_e1.grid(row=0, column=3, padx=6, pady=4)

        tk.Label(ctrl1, text="Location:", font=FONT_BODY, bg=BG).grid(
            row=0, column=4, padx=6, pady=4, sticky="e")
        is_loc1_var = tk.StringVar(value="Company Total")
        loc1_options = ["Company Total"] + loc_names_only
        loc1_cb = ttk.Combobox(ctrl1, textvariable=is_loc1_var, values=loc1_options,
                                font=FONT_BODY, state="readonly", width=18)
        loc1_cb.grid(row=0, column=5, padx=6, pady=4)

        out1 = _make_output(tab1)

        warn_var = tk.StringVar(value="")
        tk.Label(tab1, textvariable=warn_var, font=("Helvetica", 10),
                 fg="#CC6600", bg=BG).pack()

        def _update_warning(*_):
            try:
                y = int(year_e1.get())
                m = MONTH_NAMES.index(month_var.get()) + 1
                if y == date.today().year and m == date.today().month:
                    warn_var.set("⚠️  This month is still in progress — data will be incomplete.")
                else:
                    warn_var.set("")
            except ValueError:
                warn_var.set("")

        month_var.trace_add("write", _update_warning)
        year_e1.bind("<KeyRelease>", _update_warning)

        def gen_income():
            ok, err = validation.validate_year(year_e1.get())
            if not ok:
                messagebox.showerror("Validation Error", err, parent=win)
                return
            month_num = MONTH_NAMES.index(month_var.get()) + 1
            year_num  = int(year_e1.get())
            sel = is_loc1_var.get()
            if sel == "Company Total":
                loc_id_arg = None
                loc_disp   = "All Locations (Company Total)"
            else:
                loc_id_arg = self._loc_name_to_id[sel]
                loc_disp   = sel
            try:
                data = logic.get_monthly_income_statement(loc_id_arg, year_num, month_num)
                text = reports.format_income_statement(data, loc_disp, year_num, month_num)
                _display_text(out1, text)
            except Exception as exc:
                messagebox.showerror("Error", str(exc), parent=win)

        _btn(tab1, "Generate Report", gen_income, width=20, pady=4).pack(pady=4)

        # ── Tab 2: Flavor Sales ───────────────────────────────────────────────
        tab2 = tk.Frame(notebook, bg=BG)
        notebook.add(tab2, text="Flavor Sales")

        ctrl2 = tk.Frame(tab2, bg=BG)
        ctrl2.pack(pady=(10, 4))

        # Default: last completed month
        import calendar
        _t2_today = date.today()
        _t2_def_month = _t2_today.month - 1 if _t2_today.month > 1 else 12
        _t2_def_year  = _t2_today.year if _t2_today.month > 1 else _t2_today.year - 1

        tk.Label(ctrl2, text="Start Month:", font=FONT_BODY, bg=BG).grid(
            row=0, column=0, padx=6, pady=4, sticky="e")
        start_month_var = tk.StringVar(value=MONTH_NAMES[_t2_def_month - 1])
        start_month_cb  = ttk.Combobox(ctrl2, textvariable=start_month_var,
                                        values=MONTH_NAMES, font=FONT_BODY,
                                        state="readonly", width=11)
        start_month_cb.grid(row=0, column=1, padx=6, pady=4)

        tk.Label(ctrl2, text="Year:", font=FONT_BODY, bg=BG).grid(
            row=0, column=2, padx=4, pady=4, sticky="e")
        start_year_e = _entry(ctrl2, width=7, default=str(_t2_def_year))
        start_year_e.grid(row=0, column=3, padx=4, pady=4)

        tk.Label(ctrl2, text="End Month:", font=FONT_BODY, bg=BG).grid(
            row=0, column=4, padx=6, pady=4, sticky="e")
        end_month_var = tk.StringVar(value=MONTH_NAMES[_t2_def_month - 1])
        end_month_cb  = ttk.Combobox(ctrl2, textvariable=end_month_var,
                                      values=MONTH_NAMES, font=FONT_BODY,
                                      state="readonly", width=11)
        end_month_cb.grid(row=0, column=5, padx=6, pady=4)

        tk.Label(ctrl2, text="Year:", font=FONT_BODY, bg=BG).grid(
            row=0, column=6, padx=4, pady=4, sticky="e")
        end_year_e = _entry(ctrl2, width=7, default=str(_t2_def_year))
        end_year_e.grid(row=0, column=7, padx=4, pady=4)

        tk.Label(ctrl2, text="Location:", font=FONT_BODY, bg=BG).grid(
            row=0, column=8, padx=6, pady=4, sticky="e")
        loc2_var = tk.StringVar(value="All Locations")
        loc2_cb  = ttk.Combobox(ctrl2, textvariable=loc2_var,
                                  values=loc_names_with_all, font=FONT_BODY,
                                  state="readonly", width=18)
        loc2_cb.grid(row=0, column=9, padx=6, pady=4)

        out2 = _make_output(tab2)

        def gen_flavor():
            try:
                start_year_num = int(start_year_e.get())
            except (ValueError, TypeError):
                messagebox.showerror("Validation Error",
                                     "Start Year must be a valid integer.", parent=win)
                return
            try:
                end_year_num = int(end_year_e.get())
            except (ValueError, TypeError):
                messagebox.showerror("Validation Error",
                                     "End Year must be a valid integer.", parent=win)
                return

            start_month_num = MONTH_NAMES.index(start_month_var.get()) + 1
            end_month_num   = MONTH_NAMES.index(end_month_var.get()) + 1
            start_d = date(start_year_num, start_month_num, 1)
            last_day = calendar.monthrange(end_year_num, end_month_num)[1]
            end_d   = date(end_year_num, end_month_num, last_day)

            if start_d > end_d:
                messagebox.showerror("Validation Error",
                                     "Start date must be on or before end date.", parent=win)
                return

            sel = loc2_var.get()
            if sel == "All Locations":
                loc_id_arg = None
                loc_disp   = "All Locations"
            else:
                loc_id_arg = self._loc_name_to_id[sel]
                loc_disp   = sel
            try:
                data = logic.get_flavor_sales_quantity(loc_id_arg, start_d, end_d)
                text = reports.format_flavor_sales(data, loc_disp, start_d, end_d)
                _display_text(out2, text)
            except Exception as exc:
                messagebox.showerror("Error", str(exc), parent=win)

        _btn(tab2, "Generate Report", gen_flavor, width=20, pady=4).pack(pady=4)

        # ── Tab 3: Inventory Report ───────────────────────────────────────────
        tab3 = tk.Frame(notebook, bg=BG)
        notebook.add(tab3, text="Inventory Report")

        ctrl3 = tk.Frame(tab3, bg=BG)
        ctrl3.pack(pady=(10, 4))

        tk.Label(ctrl3, text="Location:", font=FONT_BODY, bg=BG).grid(
            row=0, column=0, padx=6, pady=4, sticky="e")
        loc3_var = tk.StringVar(value="All Locations")
        loc3_cb  = ttk.Combobox(ctrl3, textvariable=loc3_var,
                                  values=loc_names_with_all, font=FONT_BODY,
                                  state="readonly", width=18)
        loc3_cb.grid(row=0, column=1, padx=6, pady=4)

        out3 = _make_output(tab3)

        def gen_inv():
            sel = loc3_var.get()
            try:
                if sel == "All Locations":
                    parts = []
                    for loc in self.locations:
                        inv  = logic.get_current_inventory(loc["location_id"])
                        part = reports.format_inventory_report(inv, loc["location_name"])
                        parts.append(part)
                    _display_text(out3, "\n".join(parts))
                else:
                    loc_id_arg = self._loc_name_to_id[sel]
                    inv  = logic.get_current_inventory(loc_id_arg)
                    text = reports.format_inventory_report(inv, sel)
                    _display_text(out3, text)
            except Exception as exc:
                messagebox.showerror("Error", str(exc), parent=win)

        _btn(tab3, "Generate Report", gen_inv, width=20, pady=4).pack(pady=4)


# ── public entry point ────────────────────────────────────────────────────────

def main():
    root = tk.Tk()
    ScoopsApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
