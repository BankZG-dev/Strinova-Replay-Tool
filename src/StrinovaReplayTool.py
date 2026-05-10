"""
Strinova Replay Tool v3.1
Single-file EXE edition — works when copied anywhere.
"""

import os
import sys
import shutil
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk

APP_TITLE   = "Strinova Replay Tool"
APP_VERSION = ""
WINDOW_SIZE = "960x680"

GAMES = {
    "Strinova":  "Strinova",
    "CalabiYau": "CalabiYau",
}

ACCENT      = "#5fc7ff"
ACCENT_DARK = "#3aabee"
BG_DARK     = "#0f1115"
CARD_BG     = "#1b1f27"
CARD_BG2    = "#252a35"
TEXT_MAIN   = "#e6ecf2"
TEXT_MUTED  = "#9aa7b4"
SUCCESS     = "#4ade80"
ERROR       = "#f87171"
BORDER      = "#2f3542"
ROW_SEL     = "#1e3a5f"

# ── Helpers ───────────────────────────────────────────────────────────────────

def resource_path(rel: str) -> Path:
    """Works both in dev and inside PyInstaller --onefile bundle."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / rel

def default_demo_dir(game: str) -> Path:
    return Path.home() / "AppData" / "Local" / game / "Saved" / "Demos"

def list_demo_files(demo_dir: Path) -> list:
    if not demo_dir.exists():
        return []
    files = [f for f in demo_dir.iterdir() if f.is_file()]
    files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    return files

def human_size(path: Path) -> str:
    try:
        b = path.stat().st_size
        if b >= 1_000_000_000: return f"{b/1_000_000_000:.2f} GB"
        if b >= 1_000_000:     return f"{b/1_000_000:.1f} MB"
        return f"{b/1_000:.1f} KB"
    except Exception:
        return "?"

def backup_dir_for(demo_dir: Path) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return demo_dir / "Backups" / ts

# ── Main App ──────────────────────────────────────────────────────────────────

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.title(f"{APP_TITLE}  {APP_VERSION}")
        self.geometry(WINDOW_SIZE)
        self.minsize(780, 560)
        self.configure(fg_color=BG_DARK)

        # Set icon — works from bundle or dev folder
        for name in ("strinova_icon.ico", "app.ico", "strinova_icon_trimmed.ico"):
            p = resource_path(name)
            if p.exists():
                try:
                    self.iconbitmap(str(p))
                except Exception:
                    pass
                break

        self.selected_game     = ctk.StringVar(value=list(GAMES.keys())[0])
        self.host_path: Path | None = None
        self.inj_path:  Path | None = None
        self.do_backup         = ctk.BooleanVar(value=True)
        self._row_paths: dict  = {}
        self._refresh_after_id = None

        self._build_ui()
        self.refresh_table()

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        # Sidebar
        self.sidebar = ctk.CTkFrame(self, width=220, fg_color=CARD_BG, corner_radius=0)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        logo_frame = ctk.CTkFrame(self.sidebar, fg_color=CARD_BG2, corner_radius=0, height=70)
        logo_frame.pack(fill="x")
        logo_frame.pack_propagate(False)
        ctk.CTkLabel(logo_frame, text="⚡ Strinova",
                     font=ctk.CTkFont(size=18, weight="bold"),
                     text_color=ACCENT).pack(padx=20, pady=(18, 2))
        ctk.CTkLabel(logo_frame, text=f"Replay Tool {APP_VERSION}",
                     font=ctk.CTkFont(size=11), text_color=TEXT_MUTED).pack()

        ctk.CTkLabel(self.sidebar, text="GAME",
                     font=ctk.CTkFont(size=10, weight="bold"),
                     text_color=TEXT_MUTED).pack(anchor="w", padx=20, pady=(24, 6))

        for key in GAMES:
            rb = ctk.CTkRadioButton(
                self.sidebar, text=key, variable=self.selected_game,
                value=key, command=self._on_game_change,
                font=ctk.CTkFont(size=13), text_color=TEXT_MAIN,
                fg_color=ACCENT, hover_color=ACCENT_DARK, border_color=BORDER)
            rb.pack(anchor="w", padx=24, pady=4)

        ctk.CTkFrame(self.sidebar, height=1, fg_color=BORDER).pack(fill="x", padx=16, pady=20)

        help_text = (
            "HOW IT WORKS\n\n"
            "1. Select a host replay from your game's Demos folder.\n\n"
            "2. Browse to the downloaded .dem file you want to inject.\n\n"
            "3. Press Swap — the tool replaces the host file content "
            "while keeping its filename so the game can load it.\n\n"
            "💡 Record a short dummy replay in-game first to create the host file."
        )
        help_box = ctk.CTkTextbox(
            self.sidebar, wrap="word", fg_color=CARD_BG2,
            text_color=TEXT_MUTED, font=ctk.CTkFont(size=11),
            border_width=0, height=260, activate_scrollbars=False)
        help_box.pack(fill="x", padx=16)
        help_box.insert("end", help_text)
        help_box.configure(state="disabled")

        # Block mouse wheel on sidebar
        for widget in (self.sidebar, help_box):
            widget.bind("<MouseWheel>", lambda e: "break")
            widget.bind("<Button-4>",   lambda e: "break")
            widget.bind("<Button-5>",   lambda e: "break")

        ctk.CTkLabel(self.sidebar, text=f"© 2024  {APP_TITLE}",
                     font=ctk.CTkFont(size=10), text_color=TEXT_MUTED).pack(
                     side="bottom", pady=12)

        # Main area
        main = ctk.CTkFrame(self, fg_color=BG_DARK, corner_radius=0)
        main.pack(side="left", fill="both", expand=True)

        topbar = ctk.CTkFrame(main, fg_color=CARD_BG2, corner_radius=0, height=48)
        topbar.pack(fill="x")
        topbar.pack_propagate(False)
        ctk.CTkLabel(topbar, text="Demo Folder:",
                     font=ctk.CTkFont(size=12), text_color=TEXT_MUTED).pack(
                     side="left", padx=(20, 6), pady=12)
        self.folder_label = ctk.CTkLabel(topbar, text="",
                                         font=ctk.CTkFont(size=12), text_color=TEXT_MAIN)
        self.folder_label.pack(side="left", pady=12)
        ctk.CTkButton(topbar, text="⟳  Refresh", width=100, height=30,
                      font=ctk.CTkFont(size=12), fg_color=CARD_BG,
                      hover_color=BORDER, text_color=TEXT_MAIN,
                      border_width=1, border_color=BORDER,
                      command=self.refresh_table).pack(side="right", padx=16, pady=9)

        content = ctk.CTkFrame(main, fg_color=BG_DARK)
        content.pack(fill="both", expand=True, padx=20, pady=16)

        # Step 1 card
        step1_card = ctk.CTkFrame(content, fg_color=CARD_BG, corner_radius=12)
        step1_card.pack(fill="both", expand=True)

        step1_hdr = ctk.CTkFrame(step1_card, fg_color=CARD_BG2, corner_radius=0, height=40)
        step1_hdr.pack(fill="x")
        step1_hdr.pack_propagate(False)
        ctk.CTkLabel(step1_hdr,
                     text="  STEP 1 — Select Host Replay  (from your Demos folder)",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=ACCENT).pack(side="left", padx=16, pady=10)

        col_frame = ctk.CTkFrame(step1_card, fg_color=CARD_BG2, corner_radius=0, height=30)
        col_frame.pack(fill="x", pady=(1, 0))
        col_frame.pack_propagate(False)
        for text, width, anchor in [
            ("Filename", 420, "w"), ("Size", 80, "center"), ("Date Modified", 160, "center")
        ]:
            ctk.CTkLabel(col_frame, text=text, width=width,
                         font=ctk.CTkFont(size=11, weight="bold"),
                         text_color=TEXT_MUTED, anchor=anchor).pack(
                         side="left", padx=(12 if anchor == "w" else 0, 0))

        # Native canvas for smooth scrolling
        list_outer = tk.Frame(step1_card, bg=BG_DARK)
        list_outer.pack(fill="both", expand=True)

        self._canvas = tk.Canvas(list_outer, bg=BG_DARK, bd=0,
                                 highlightthickness=0, relief="flat")
        self._scrollbar = ctk.CTkScrollbar(list_outer, orientation="vertical",
                                           command=self._canvas.yview,
                                           fg_color=CARD_BG, button_color=BORDER,
                                           button_hover_color=TEXT_MUTED)
        self._scrollbar.pack(side="right", fill="y")
        self._canvas.pack(side="left", fill="both", expand=True)
        self._canvas.configure(yscrollcommand=self._scrollbar.set)

        self.list_frame = tk.Frame(self._canvas, bg=BG_DARK)
        self._canvas_window = self._canvas.create_window(
            (0, 0), window=self.list_frame, anchor="nw")

        # Fix: update scrollregion AND keep list_frame width = canvas width
        self._canvas.bind("<Configure>",    self._on_canvas_resize)
        self.list_frame.bind("<Configure>", self._on_frame_configure)
        self._canvas.bind("<MouseWheel>",   self._on_mousewheel)
        self._canvas.bind("<Button-4>",     self._on_mousewheel)
        self._canvas.bind("<Button-5>",     self._on_mousewheel)
        self.list_frame.bind("<MouseWheel>", self._on_mousewheel)

        self.host_status = ctk.CTkLabel(step1_card, text="No replay selected",
                                        font=ctk.CTkFont(size=11), text_color=TEXT_MUTED)
        self.host_status.pack(anchor="w", padx=16, pady=6)

        # Step 2 + actions
        bottom = ctk.CTkFrame(content, fg_color="transparent")
        bottom.pack(fill="x", pady=(12, 0))

        step2_card = ctk.CTkFrame(bottom, fg_color=CARD_BG, corner_radius=12)
        step2_card.pack(fill="x")

        step2_inner = ctk.CTkFrame(step2_card, fg_color="transparent")
        step2_inner.pack(fill="x", padx=16, pady=12)

        ctk.CTkLabel(step2_inner, text="STEP 2 — Select Injection File",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=ACCENT).grid(row=0, column=0, sticky="w", pady=(0, 8))

        self.inj_label = ctk.CTkLabel(step2_inner, text="No file selected",
                                      font=ctk.CTkFont(size=12), text_color=TEXT_MUTED)
        self.inj_label.grid(row=1, column=0, sticky="w")

        ctk.CTkButton(step2_inner, text="Browse File…", width=130, height=34,
                      font=ctk.CTkFont(size=13), fg_color=CARD_BG2,
                      hover_color=BORDER, text_color=TEXT_MAIN,
                      border_width=1, border_color=BORDER,
                      command=self.browse_injection).grid(row=1, column=1, padx=(16, 0))

        act = ctk.CTkFrame(bottom, fg_color="transparent")
        act.pack(fill="x", pady=(10, 0))

        ctk.CTkCheckBox(act, text="Backup before swap", variable=self.do_backup,
                        font=ctk.CTkFont(size=12), text_color=TEXT_MUTED,
                        fg_color=ACCENT, hover_color=ACCENT_DARK,
                        border_color=BORDER).pack(side="left")

        ctk.CTkButton(act, text="♻  Restore from Backup", width=180, height=38,
                      font=ctk.CTkFont(size=13), fg_color=CARD_BG,
                      hover_color=CARD_BG2, text_color=TEXT_MUTED,
                      border_width=1, border_color=BORDER,
                      command=self.restore_from_backup).pack(side="right", padx=(8, 0))

        ctk.CTkButton(act, text="⚡  Swap Now", width=140, height=38,
                      font=ctk.CTkFont(size=14, weight="bold"),
                      fg_color=ACCENT, hover_color=ACCENT_DARK,
                      text_color="#0f1115",
                      command=self.swap_now).pack(side="right")

        self.status_bar = ctk.CTkLabel(main, text="Ready.",
                                       font=ctk.CTkFont(size=11),
                                       text_color=TEXT_MUTED, anchor="w")
        self.status_bar.pack(fill="x", padx=24, pady=(0, 8))

        self._update_folder_label()

    # ── Scroll ────────────────────────────────────────────────────────────────

    def _on_canvas_resize(self, event):
        self._canvas.itemconfig(self._canvas_window, width=event.width)
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    def _on_frame_configure(self, event):
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    def _on_mousewheel(self, event):
        if event.num == 4:
            self._canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self._canvas.yview_scroll(1, "units")
        else:
            self._canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _bind_wheel(self, widget):
        widget.bind("<MouseWheel>", self._on_mousewheel)
        widget.bind("<Button-4>",   self._on_mousewheel)
        widget.bind("<Button-5>",   self._on_mousewheel)

    # ── Logic ─────────────────────────────────────────────────────────────────

    def _update_folder_label(self):
        d = default_demo_dir(GAMES[self.selected_game.get()])
        self.folder_label.configure(text=str(d))

    def _on_game_change(self):
        self.host_path = None
        self.host_status.configure(text="No replay selected", text_color=TEXT_MUTED)
        self._update_folder_label()
        if self._refresh_after_id:
            self.after_cancel(self._refresh_after_id)
        self._refresh_after_id = self.after(80, self.refresh_table)

    def _set_status(self, msg: str, color: str = TEXT_MUTED):
        self.status_bar.configure(text=msg, text_color=color)

    def refresh_table(self):
        self._refresh_after_id = None
        self._row_paths = {}
        for w in self.list_frame.winfo_children():
            w.destroy()

        game     = self.selected_game.get()
        demo_dir = default_demo_dir(GAMES[game])
        files    = list_demo_files(demo_dir)

        if not files:
            tk.Label(self.list_frame,
                     text=f"No replay files found in:\n{demo_dir}",
                     bg=BG_DARK, fg=TEXT_MUTED,
                     font=("Segoe UI", 11), justify="center").pack(pady=30)
            self._set_status(f"No files in {demo_dir}")
            self._canvas.yview_moveto(0)
            return

        self._set_status(f"{len(files)} replay(s) found in {demo_dir}")

        for i, f in enumerate(files):
            row_bg = CARD_BG if i % 2 == 0 else CARD_BG2

            row = tk.Frame(self.list_frame, bg=row_bg, height=36)
            row.pack(fill="x", padx=2, pady=1)
            row.pack_propagate(False)

            name_lbl = tk.Label(row, text=f.name, width=52,
                                bg=row_bg, fg=TEXT_MAIN,
                                font=("Segoe UI", 11), anchor="w")
            name_lbl.pack(side="left", padx=(12, 0))

            size_lbl = tk.Label(row, text=human_size(f), width=10,
                                bg=row_bg, fg=TEXT_MUTED,
                                font=("Segoe UI", 10), anchor="center")
            size_lbl.pack(side="left")

            mtime = datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
            date_lbl = tk.Label(row, text=mtime, width=18,
                                bg=row_bg, fg=TEXT_MUTED,
                                font=("Segoe UI", 10), anchor="center")
            date_lbl.pack(side="left")

            for w in (row, name_lbl, size_lbl, date_lbl):
                w.bind("<Button-1>",  lambda e, p=f, r=row: self._select_row(p, r))
                w.bind("<Enter>",     lambda e, r=row, rb=row_bg: self._on_row_enter(r, rb))
                w.bind("<Leave>",     lambda e, r=row, rb=row_bg: self._on_row_leave(r, rb))
                self._bind_wheel(w)

            self._row_paths[id(row)] = (f, row, row_bg)

        self._canvas.yview_moveto(0)

    def _set_row_color(self, row: tk.Frame, color: str):
        row.configure(bg=color)
        for c in row.winfo_children():
            c.configure(bg=color)

    def _on_row_enter(self, row: tk.Frame, row_bg: str):
        # Only highlight if this row is NOT the selected one
        if self.host_path != self._row_paths.get(id(row), (None,))[0]:
            self._set_row_color(row, BORDER)

    def _on_row_leave(self, row: tk.Frame, row_bg: str):
        # Restore original color only if not selected
        if self.host_path != self._row_paths.get(id(row), (None,))[0]:
            self._set_row_color(row, row_bg)

    def _get_selected_row(self):
        for _, (p, r, _) in self._row_paths.items():
            if p == self.host_path:
                return r
        return None

    def _select_row(self, path: Path, selected_row: tk.Frame):
        # Deselect all
        for _, (_, r, bg) in self._row_paths.items():
            self._set_row_color(r, bg)
        # Select
        self._set_row_color(selected_row, ROW_SEL)
        self.host_path = path
        self.host_status.configure(text=f"✓  Selected: {path.name}", text_color=SUCCESS)
        self._set_status(f"Host: {path.name}", SUCCESS)

    def browse_injection(self):
        p = filedialog.askopenfilename(
            title="Select downloaded demo file",
            filetypes=[("Demo files", "*.dem *.replay *.bin *.rep"), ("All files", "*.*")])
        if p:
            self.inj_path = Path(p)
            self.inj_label.configure(
                text=f"✓  {self.inj_path.name}  ({human_size(self.inj_path)})",
                text_color=SUCCESS)
            self._set_status(f"Injection: {self.inj_path.name}", SUCCESS)

    def swap_now(self):
        if not self.host_path:
            messagebox.showwarning("No Host Selected", "Please select a host replay in Step 1.")
            return
        if not self.inj_path or not self.inj_path.exists():
            messagebox.showwarning("No Injection File", "Please select a valid file in Step 2.")
            return

        backup_to = None
        if self.do_backup.get():
            bdir = backup_dir_for(self.host_path.parent)
            bdir.mkdir(parents=True, exist_ok=True)
            backup_to = bdir / self.host_path.name
            shutil.copy2(self.host_path, backup_to)

        try:
            temp = self.host_path.with_suffix(".tmp_swap")
            shutil.copy2(self.inj_path, temp)
            temp.replace(self.host_path)
        except PermissionError:
            messagebox.showerror("Permission Error",
                                 f"Cannot write to:\n{self.host_path}\n\nClose the game and try again.")
            return
        except Exception as e:
            messagebox.showerror("Error", f"Swap failed:\n{e}")
            return

        msg = "Swap complete!"
        if backup_to:
            msg += f"\nBackup saved to:\n{backup_to}"
        messagebox.showinfo("Success", msg)
        self._set_status("Swap complete.", SUCCESS)
        self.refresh_table()

    def restore_from_backup(self):
        game         = self.selected_game.get()
        demo_dir     = default_demo_dir(GAMES[game])
        backups_root = demo_dir / "Backups"

        if not backups_root.is_dir():
            messagebox.showinfo("No Backups", "No backup folder found yet.")
            return

        backup_dir = filedialog.askdirectory(
            title="Select backup timestamp folder", initialdir=str(backups_root))
        if not backup_dir:
            return

        bpath = Path(backup_dir)
        if not bpath.is_dir() or bpath.parent != backups_root:
            messagebox.showwarning("Invalid Folder", "Choose a valid backup timestamp folder.")
            return

        files = list(bpath.iterdir())
        if not messagebox.askyesno("Restore",
                f"Restore {len(files)} file(s) from:\n{bpath}\n\ninto:\n{demo_dir}\n\n"
                "Overwrite existing files?"):
            return

        try:
            for f in files:
                shutil.copy2(f, demo_dir / f.name)
            messagebox.showinfo("Restored", "Restore complete.")
            self._set_status("Restore complete.", SUCCESS)
            self.refresh_table()
        except Exception as e:
            messagebox.showerror("Error", f"Restore failed:\n{e}")


if __name__ == "__main__":
    app = App()
    app.mainloop()