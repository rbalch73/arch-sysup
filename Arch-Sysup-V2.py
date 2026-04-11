#!/usr/bin/env python3
"""
Arch-Sysup — Arch Linux GUI system manager
Tabs: Updates | Search & Install | Package Info | System Stats | Orphans | Repositories
Requires: python, tk  (sudo pacman -S tk)
"""

import tkinter as tk
from tkinter import ttk, messagebox
import subprocess, threading, shutil, re, os, time

# ── Theme palettes ────────────────────────────────────────────────────────────
THEMES = {
    "dark": {
        "BG":"#0e1117","BG_PANEL":"#161b24","BG_ROW_ALT":"#12171f",
        "BG_INPUT":"#0d1117","BG_HDR":"#1c2230","BG_LOG":"#0a0e14",
        "FG":"#c9d1d9","FG_DIM":"#6e7681","ACCENT":"#58a6ff",
        "BORDER":"#30363d","BTN_BG":"#21262d","BTN_HOVER":"#30363d",
        "VER_OLD":"#f85149","VER_NEW":"#3fb950",
        "KERNEL_FG":"#ff4444","KERNEL_BG":"#2d0f0f",
        "BTN_GREEN":"#238636","BTN_GREEN_H":"#2ea043",
        "BTN_RED":"#b62324","BTN_RED_H":"#d32f2f",
        "BTN_ACCENT":"#1f4788","BTN_ACCT_H":"#2563b0",
        "BTN_ORANGE":"#9a5a00","BTN_ORNG_H":"#c47200",
        "BTN_PURPLE":"#6e40c9","BTN_PURP_H":"#8957e5",
        "REPO_CORE":"#e3b341","REPO_EXTRA":"#3fb950","REPO_MULTI":"#39c5cf",
        "REPO_CHAOT":"#58a6ff","REPO_AUR":"#bc8cff","REPO_DEF":"#8b949e",
        "CHART_1":"#58a6ff","CHART_2":"#3fb950","CHART_3":"#f85149",
        "CHART_4":"#e3b341","CHART_5":"#bc8cff","CHART_BG":"#0d1117",
        "TOGGLE_ICON":"☀","TOGGLE_TIP":"Switch to Light Mode",
    },
    "light": {
        "BG":"#f6f8fa","BG_PANEL":"#ffffff","BG_ROW_ALT":"#f0f2f4",
        "BG_INPUT":"#ffffff","BG_HDR":"#e8ecf0","BG_LOG":"#1c1c1c",
        "FG":"#1f2328","FG_DIM":"#656d76","ACCENT":"#0969da",
        "BORDER":"#d0d7de","BTN_BG":"#e6edf3","BTN_HOVER":"#d0d7de",
        "VER_OLD":"#cf222e","VER_NEW":"#1a7f37",
        "KERNEL_FG":"#cf222e","KERNEL_BG":"#ffebe9",
        "BTN_GREEN":"#1a7f37","BTN_GREEN_H":"#116329",
        "BTN_RED":"#cf222e","BTN_RED_H":"#a40e26",
        "BTN_ACCENT":"#0969da","BTN_ACCT_H":"#0550ae",
        "BTN_ORANGE":"#bc4c00","BTN_ORNG_H":"#953800",
        "BTN_PURPLE":"#6639ba","BTN_PURP_H":"#8250df",
        "REPO_CORE":"#9a6700","REPO_EXTRA":"#1a7f37","REPO_MULTI":"#0969da",
        "REPO_CHAOT":"#6639ba","REPO_AUR":"#8250df","REPO_DEF":"#57606a",
        "CHART_1":"#0969da","CHART_2":"#1a7f37","CHART_3":"#cf222e",
        "CHART_4":"#9a6700","CHART_5":"#8250df","CHART_BG":"#f0f2f4",
        "TOGGLE_ICON":"☾","TOGGLE_TIP":"Switch to Dark Mode",
    },
}
T = dict(THEMES["dark"])
_current_theme = "dark"

MONO   = ("Monospace", 10)
MONO_B = ("Monospace", 10, "bold")
MONO_S = ("Monospace", 9)
MONO_SB= ("Monospace", 9, "bold")
MONO_L = ("Monospace", 11)
TITLE  = ("Monospace", 16, "bold")
PACMAN_CONF = "/etc/pacman.conf"


# ── Pure helpers ──────────────────────────────────────────────────────────────
def repo_color(repo):
    return {"core":T["REPO_CORE"],"extra":T["REPO_EXTRA"],"multilib":T["REPO_MULTI"],
            "chaotic-aur":T["REPO_CHAOT"],"aur":T["REPO_AUR"]}.get(repo.lower(),T["REPO_DEF"])

def repo_order(repo):
    return {"core":0,"extra":1,"multilib":2,"chaotic-aur":3,"aur":4}.get(repo.lower(),5)

def is_kernel(pkg):
    return bool(re.match(r'^linux(-lts|-zen|-hardened|-rt|-cachyos|-xanmod|-tkg|-mainline)?$',pkg)
                or re.match(r'^linux-\d',pkg))

def split_ver_diff(ver, other):
    i=0
    while i<len(ver) and i<len(other) and ver[i]==other[i]: i+=1
    return ver[:i], ver[i:]

def detect_aur_helper():
    for h in ("yay","paru"):
        if shutil.which(h): return h
    return None

def run_cmd(cmd, timeout=30):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip()
    except Exception:
        return ""

def fmt_bytes(n):
    for u in ("B","KB","MB","GB","TB"):
        if n < 1024: return f"{n:.1f} {u}"
        n /= 1024
    return f"{n:.1f} PB"


# ── pacman.conf helpers ───────────────────────────────────────────────────────
def parse_pacman_conf(path=PACMAN_CONF):
    sections, current, preamble = [], None, []
    try:
        with open(path) as f: raw = f.readlines()
    except PermissionError:
        return [], []
    for line in raw:
        s = line.strip()
        m = re.match(r'^\[([^\]]+)\]', s)
        if m:
            if current: sections.append(current)
            n = m.group(1)
            current = {"name":n,"enabled":True,"lines":[line],
                       "type":"options" if n=="options" else "repo"}; continue
        mc = re.match(r'^#\s*\[([^\]]+)\]', s)
        if mc:
            if current: sections.append(current)
            n = mc.group(1)
            current = {"name":n,"enabled":False,"lines":[line],
                       "type":"options" if n=="options" else "repo"}; continue
        if current is not None: current["lines"].append(line)
        else: preamble.append(line)
    if current: sections.append(current)
    return preamble, sections

def write_pacman_conf(preamble, sections):
    out = list(preamble)
    for sec in sections:
        if sec["type"]=="options": out.extend(sec["lines"]); continue
        lines = sec["lines"]
        if not lines: continue
        out.append(f"[{sec['name']}]\n" if sec["enabled"] else f"#[{sec['name']}]\n")
        for ln in lines[1:]:
            s = ln.strip()
            if sec["enabled"]:
                m = re.match(r'^#\s*((?:Include|Server)\s*=.+)', s)
                out.append(m.group(1)+"\n" if m else ln)
            else:
                if re.match(r'^(Include|Server)\s*=', s):
                    out.append("#"+ln if not ln.startswith("#") else ln)
                else: out.append(ln)
    return "".join(out)


# ── Button factory ────────────────────────────────────────────────────────────
def _make_btn(parent, text, cmd, bg_key, hover_key, fg_key="FG", state="normal"):
    def _col(k): return T[k] if not k.startswith("#") else k
    btn = tk.Label(parent, text=text, font=MONO_B,
                   bg=_col(bg_key), fg=_col(fg_key),
                   padx=14, pady=6, cursor="hand2", relief="flat")
    btn._bg_key=bg_key; btn._hover_key=hover_key; btn._fg_key=fg_key
    btn._disabled=(state=="disabled")
    def _click(e):
        if not btn._disabled: cmd()
    def _enter(e):
        if not btn._disabled: btn.config(bg=_col(hover_key))
    def _leave(e): btn.config(bg=_col(bg_key))
    btn.bind("<Button-1>",_click); btn.bind("<Enter>",_enter); btn.bind("<Leave>",_leave)
    if btn._disabled: btn.config(fg=T["FG_DIM"], cursor="")
    def enable():
        btn._disabled=False; btn.config(fg=_col(fg_key),cursor="hand2",bg=_col(bg_key))
    def disable():
        btn._disabled=True; btn.config(fg=T["FG_DIM"],cursor="",bg=_col(bg_key))
    def retheme():
        btn.config(bg=_col(bg_key), fg=T["FG_DIM"] if btn._disabled else _col(fg_key))
    btn.enable=enable; btn.disable=disable; btn.retheme=retheme
    return btn


# ── Sudo dialog ───────────────────────────────────────────────────────────────
class SudoDialog(tk.Toplevel):
    def __init__(self, parent, prompt="Enter sudo password:"):
        super().__init__(parent)
        self.result=None
        self.title("Authentication Required")
        self.configure(bg=T["BG"])
        self.geometry("440x230"); self.resizable(False,False)
        self.transient(parent)
        tk.Label(self,text="🔒  Authentication Required",font=MONO_B,bg=T["BG"],fg=T["ACCENT"]).pack(pady=(22,4))
        tk.Label(self,text=prompt,font=MONO_S,bg=T["BG"],fg=T["FG"],wraplength=390,justify="center").pack(pady=(0,12))
        ef=tk.Frame(self,bg=T["BG"]); ef.pack()
        self._entry=tk.Entry(ef,show="●",font=MONO,bg=T["BG_INPUT"],fg=T["FG"],
                             insertbackground=T["FG"],relief="flat",bd=0,width=30,
                             highlightthickness=1,highlightcolor=T["ACCENT"],highlightbackground=T["BORDER"])
        self._entry.pack(ipady=6,padx=2); self._entry.focus_set()
        self._entry.bind("<Return>",lambda e:self._submit())
        self._err=tk.Label(self,text="",font=MONO_S,bg=T["BG"],fg=T["VER_OLD"])
        self._err.pack(pady=(4,0))
        br=tk.Frame(self,bg=T["BG"]); br.pack(pady=(8,0))
        _make_btn(br,"  Authenticate  ",self._submit,"BTN_GREEN","BTN_GREEN_H","#ffffff").pack(side="left",padx=(0,10))
        _make_btn(br,"  Cancel  ",self._cancel,"BTN_BG","BTN_HOVER").pack(side="left")
        self.protocol("WM_DELETE_WINDOW",self._cancel)
        self.update_idletasks(); self.grab_set()
    def _submit(self): self.result=self._entry.get(); self.destroy()
    def _cancel(self): self.result=None; self.destroy()
    def show_error(self,msg): self._err.config(text=msg); self._entry.delete(0,"end"); self._entry.focus_set()

def verify_sudo(pw):
    r=subprocess.run(["sudo","-S","-v"],input=pw+"\n",capture_output=True,text=True)
    return r.returncode==0

def run_sudo_cmd(pw, cmd):
    proc=subprocess.Popen(["sudo","-S","-p",""]+cmd,
                          stdin=subprocess.PIPE,stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT,text=True,bufsize=1)
    try: proc.stdin.write(pw+"\n"); proc.stdin.flush(); proc.stdin.close()
    except BrokenPipeError: pass
    return proc


# ══════════════════════════════════════════════════════════════════════════════
# MAIN APPLICATION
# ══════════════════════════════════════════════════════════════════════════════
class SysUpApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Arch-Sysup — System Manager")
        self.configure(bg=T["BG"])
        self.geometry("1120x780"); self.minsize(900,580); self.resizable(True,True)
        self.aur_helper   = detect_aur_helper()
        self.updates      = []
        self.kernel_found = False
        self._sudo_pw     = None
        self._themed_widgets = []
        self._build_ui()
        self.after(100, self._check_updates)
        self.after(200, self._refresh_stats)

    # ── Theme registry ────────────────────────────────────────────────────────
    def _tw(self, w, **props):
        self._themed_widgets.append((w,props)); return w

    def _apply_theme(self):
        for w,props in self._themed_widgets:
            try:
                w.config(**{k:T[v] if not v.startswith("#") else v for k,v in props.items()})
            except Exception: pass
        for w,_ in self._themed_widgets:
            if hasattr(w,"retheme"): w.retheme()
        ttk.Style(self).configure("Vertical.TScrollbar",
            background=T["BTN_BG"],troughcolor=T["BG_PANEL"],
            arrowcolor=T["FG_DIM"],bordercolor=T["BORDER"])
        if hasattr(self,"_check_boxes"):
            for cb in self._check_boxes:
                if hasattr(cb,"_redraw"): cb._redraw()
        self._retheme_search_rows()
        self._retheme_update_rows()
        if hasattr(self,"_stats_canvas"): self._draw_stats_charts()
        if hasattr(self,"theme_btn"):
            nm = "Light" if _current_theme=="dark" else "Dark"
            self.theme_btn.config(text=f" {T['TOGGLE_ICON']}  {nm} Mode ",fg=T["FG"],bg=T["BTN_BG"])
        self.configure(bg=T["BG"])

    def _retheme_search_rows(self):
        if not hasattr(self,"_src_row_frames"): return
        for row,bg_key in self._src_row_frames:
            try:
                bg=T[bg_key]; row.config(bg=bg)
                for ch in row.winfo_children():
                    if isinstance(ch,tk.Canvas):
                        ch.config(bg=bg)
                        if hasattr(ch,"_redraw"): ch._redraw()
                        continue
                    try:
                        cfg=ch.cget("fg"); ch.config(bg=bg)
                        fm={THEMES["dark"]["FG_DIM"]:T["FG_DIM"],THEMES["light"]["FG_DIM"]:T["FG_DIM"],
                            THEMES["dark"]["FG"]:T["FG"],THEMES["light"]["FG"]:T["FG"],
                            THEMES["dark"]["VER_NEW"]:T["VER_NEW"],THEMES["light"]["VER_NEW"]:T["VER_NEW"]}
                        if cfg in fm: ch.config(fg=fm[cfg])
                        else:
                            for rk in ("REPO_CORE","REPO_EXTRA","REPO_MULTI","REPO_CHAOT","REPO_AUR","REPO_DEF"):
                                if cfg in (THEMES["dark"][rk],THEMES["light"][rk]):
                                    ch.config(fg=T[rk]); break
                    except Exception: pass
            except Exception: pass

    def _retheme_update_rows(self):
        if not hasattr(self,"upd_rows"): return
        for row in self.upd_rows.winfo_children():
            try:
                cbg=row.cget("bg")
                if cbg in (THEMES["dark"]["KERNEL_BG"],THEMES["light"]["KERNEL_BG"]): nbg=T["KERNEL_BG"]
                elif cbg in (THEMES["dark"]["BG_ROW_ALT"],THEMES["light"]["BG_ROW_ALT"]): nbg=T["BG_ROW_ALT"]
                else: nbg=T["BG_PANEL"]
                row.config(bg=nbg)
                for ch in row.winfo_children():
                    try:
                        cfg=ch.cget("fg"); ch.config(bg=nbg)
                        fm={THEMES["dark"]["FG_DIM"]:T["FG_DIM"],THEMES["light"]["FG_DIM"]:T["FG_DIM"],
                            THEMES["dark"]["FG"]:T["FG"],THEMES["light"]["FG"]:T["FG"],
                            THEMES["dark"]["KERNEL_FG"]:T["KERNEL_FG"],THEMES["light"]["KERNEL_FG"]:T["KERNEL_FG"],
                            THEMES["dark"]["VER_OLD"]:T["VER_OLD"],THEMES["light"]["VER_OLD"]:T["VER_OLD"],
                            THEMES["dark"]["VER_NEW"]:T["VER_NEW"],THEMES["light"]["VER_NEW"]:T["VER_NEW"]}
                        if cfg in fm: ch.config(fg=fm[cfg])
                        else:
                            for rk in ("REPO_CORE","REPO_EXTRA","REPO_MULTI","REPO_CHAOT","REPO_AUR","REPO_DEF"):
                                if cfg in (THEMES["dark"][rk],THEMES["light"][rk]):
                                    ch.config(fg=T[rk]); break
                    except Exception: pass
            except Exception: pass

    def _toggle_theme(self):
        global T,_current_theme
        _current_theme="light" if _current_theme=="dark" else "dark"
        T.update(THEMES[_current_theme]); self._apply_theme()

    # ── Shell ─────────────────────────────────────────────────────────────────
    def _build_ui(self):
        hdr=self._tw(tk.Frame(self,bg=T["BG"],pady=12),bg="BG")
        hdr.pack(fill="x",padx=24)
        lbl=self._tw(tk.Label(hdr,text="⟳  Arch-Sysup",font=TITLE,bg=T["BG"],fg=T["ACCENT"]),bg="BG",fg="ACCENT")
        lbl.pack(side="left")
        self.theme_btn=tk.Label(hdr,text=f" {T['TOGGLE_ICON']}  Light Mode ",font=MONO_B,
                                bg=T["BTN_BG"],fg=T["FG"],cursor="hand2",padx=6,pady=4,relief="flat")
        self.theme_btn.pack(side="right",padx=(8,0))
        self.theme_btn.bind("<Button-1>",lambda e:self._toggle_theme())
        self.theme_btn.bind("<Enter>",lambda e:self.theme_btn.config(bg=T["BTN_HOVER"]))
        self.theme_btn.bind("<Leave>",lambda e:self.theme_btn.config(bg=T["BTN_BG"]))
        self._tw(self.theme_btn,bg="BTN_BG",fg="FG")
        self.status_lbl=self._tw(tk.Label(hdr,text="Initialising…",font=MONO,bg=T["BG"],fg=T["FG_DIM"]),bg="BG",fg="FG_DIM")
        self.status_lbl.pack(side="right")
        self._tw(tk.Frame(self,bg=T["BORDER"],height=1),bg="BORDER").pack(fill="x")

        # Tab bar
        self.tab_bar=self._tw(tk.Frame(self,bg=T["BG_PANEL"]),bg="BG_PANEL")
        self.tab_bar.pack(fill="x")
        self._tab_btns={}; self._pages={}; self._active_tab=None
        TABS=("Updates","Search & Install","Package Info","System Stats","Orphans","Repositories","Mirrors")
        for name in TABS:
            b=tk.Label(self.tab_bar,text=name,font=MONO_B,bg=T["BG_PANEL"],fg=T["FG_DIM"],
                       padx=16,pady=10,cursor="hand2")
            b.pack(side="left")
            b.bind("<Button-1>",lambda e,n=name:self._switch_tab(n))
            self._tab_btns[name]=b; self._tw(b,bg="BG_PANEL",fg="FG_DIM")
        self._tw(tk.Frame(self,bg=T["BORDER"],height=1),bg="BORDER").pack(fill="x")

        self.page_container=self._tw(tk.Frame(self,bg=T["BG"]),bg="BG")
        self.page_container.pack(fill="both",expand=True)

        self._build_updates_page()
        self._build_search_page()
        self._build_info_page()
        self._build_stats_page()
        self._build_orphans_page()
        self._build_repos_page()
        self._build_mirrors_page()

        # Shared log
        self._tw(tk.Frame(self,bg=T["BORDER"],height=1),bg="BORDER").pack(fill="x")
        self.log_frame=self._tw(tk.Frame(self,bg=T["BG"]),bg="BG")
        self.log_text=tk.Text(self.log_frame,bg=T["BG_LOG"],fg=T["FG"],
                              font=("Monospace",9),relief="flat",bd=0,
                              state="disabled",wrap="word",height=10)
        self._tw(self.log_text,bg="BG_LOG",fg="FG")
        lsb=ttk.Scrollbar(self.log_frame,command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=lsb.set)
        lsb.pack(side="right",fill="y"); self.log_text.pack(fill="both",expand=True)
        self._setup_scroll()
        self._switch_tab("Updates")

    def _switch_tab(self, name):
        if self._active_tab==name: return
        self._active_tab=name
        for n,b in self._tab_btns.items():
            b.config(fg=T["ACCENT"] if n==name else T["FG_DIM"],
                     bg=T["BG"]     if n==name else T["BG_PANEL"])
        for n,p in self._pages.items():
            if n==name: p.pack(fill="both",expand=True)
            else: p.pack_forget()
        if name=="Repositories": self._reload_repos_view()
        if name=="Orphans":      self._scan_orphans()
        if name=="System Stats": self._refresh_stats()
        if name=="Mirrors":      self._load_mirror_conf()

    def _setup_scroll(self):
        _canvases={"Updates":"upd_canvas","Search & Install":"src_canvas",
                   "Package Info":"info_canvas","Orphans":"orph_canvas",
                   "Repositories":"repo_canvas","Mirrors":"mir_canvas"}
        def _get():
            c=_canvases.get(self._active_tab)
            return getattr(self,c,None) if c else None
        def _scroll(d):
            c=_get()
            if c: c.yview_scroll(d,"units")
        self.bind_all("<Button-4>",lambda e:_scroll(-2))
        self.bind_all("<Button-5>",lambda e:_scroll(2))
        def _mw(e):
            _scroll(-2 if e.delta>0 else 2)
        self.bind_all("<MouseWheel>",_mw)
        self.bind_all("<4>",lambda e:_scroll(-2))
        self.bind_all("<5>",lambda e:_scroll(2))

    # ══════════════════════════════════════════════════════════════════════════
    # UPDATES TAB
    # ══════════════════════════════════════════════════════════════════════════
    def _build_updates_page(self):
        page=self._tw(tk.Frame(self.page_container,bg=T["BG"]),bg="BG")
        self._pages["Updates"]=page
        outer=self._tw(tk.Frame(page,bg=T["BG_PANEL"]),bg="BG_PANEL")
        outer.pack(fill="both",expand=True)
        hdr=self._tw(tk.Frame(outer,bg=T["BG_HDR"],pady=6),bg="BG_HDR")
        hdr.pack(fill="x")
        for i,(l,w) in enumerate([("Repo",14),("Package",30),("Old Version",22),("New Version",22)]):
            self._tw(tk.Label(hdr,text=l,font=MONO_SB,bg=T["BG_HDR"],fg=T["FG_DIM"],width=w,anchor="w"),
                     bg="BG_HDR",fg="FG_DIM").pack(side="left",padx=(20 if i==0 else 4,0))
        self.upd_canvas=self._tw(tk.Canvas(outer,bg=T["BG_PANEL"],highlightthickness=0,bd=0),bg="BG_PANEL")
        usb=ttk.Scrollbar(outer,orient="vertical",command=self.upd_canvas.yview)
        self.upd_canvas.configure(yscrollcommand=usb.set)
        usb.pack(side="right",fill="y"); self.upd_canvas.pack(side="left",fill="both",expand=True)
        self.upd_rows=self._tw(tk.Frame(self.upd_canvas,bg=T["BG_PANEL"]),bg="BG_PANEL")
        self.upd_win=self.upd_canvas.create_window((0,0),window=self.upd_rows,anchor="nw")
        self.upd_rows.bind("<Configure>",lambda e:self.upd_canvas.configure(scrollregion=self.upd_canvas.bbox("all")))
        self.upd_canvas.bind("<Configure>",lambda e:self.upd_canvas.itemconfig(self.upd_win,width=e.width))
        self._tw(tk.Frame(page,bg=T["BORDER"],height=1),bg="BORDER").pack(fill="x")
        bot=self._tw(tk.Frame(page,bg=T["BG"],pady=10),bg="BG"); bot.pack(fill="x",padx=24)
        self.count_lbl=self._tw(tk.Label(bot,text="",font=MONO,bg=T["BG"],fg=T["FG_DIM"]),bg="BG",fg="FG_DIM")
        self.count_lbl.pack(side="left")
        br=self._tw(tk.Frame(bot,bg=T["BG"]),bg="BG"); br.pack(side="right")
        self.sync_btn=_make_btn(br,"💾  Sync DBs",self._run_sync,"BTN_BG","BTN_HOVER")
        self.sync_btn.pack(side="left",padx=(0,8)); self._tw(self.sync_btn)
        self.refresh_btn=_make_btn(br,"↻  Refresh",self._check_updates,"BTN_BG","BTN_HOVER")
        self.refresh_btn.pack(side="left",padx=(0,8)); self._tw(self.refresh_btn)
        self.update_btn=_make_btn(br,"▶  Update All",self._run_updates,"BTN_GREEN","BTN_GREEN_H","#ffffff",state="disabled")
        self.update_btn.pack(side="left"); self._tw(self.update_btn)

    def _check_updates(self):
        self.update_btn.disable(); self.refresh_btn.disable()
        for w in self.upd_rows.winfo_children(): w.destroy()
        self._hide_log(); self._set_status("Checking for updates…",T["ACCENT"])
        self.count_lbl.config(text="")
        threading.Thread(target=self._fetch_updates,daemon=True).start()

    def _fetch_updates(self):
        self.after(0, lambda: self._set_status("Checking for updates...", T["ACCENT"]))
        parsed = []

        # 1. Get official updates using 'checkupdates'
        try:
            off_res = subprocess.run(["checkupdates"], capture_output=True, text=True)
            if off_res.returncode == 0:
                for line in off_res.stdout.splitlines():
                    parts = line.split()
                    if len(parts) >= 4: # Format: pkgname oldver -> newver
                        parsed.append((parts[0], parts[1], parts[3]))
        except Exception:
            pass

        # 2. Get AUR updates using helper
        if self.aur_helper:
            try:
                aur_res = subprocess.run([self.aur_helper, "-Qua"], capture_output=True, text=True)
                if aur_res.returncode == 0:
                    for line in aur_res.stdout.splitlines():
                        parts = line.split()
                        if len(parts) >= 4:
                            parsed.append((parts[0], parts[1], parts[3]))
            except Exception:
                pass

        if not parsed:
            self.after(0, self._show_up_to_date)
            return

        # Move metadata processing to the background thread to avoid UI freeze
        self._process_parsed_updates_bg(parsed)

    def _process_parsed_updates_bg(self, parsed):
        self.after(0, lambda: self._set_status(f"Processing {len(parsed)} updates...", T["ACCENT"]))

        updates = []
        kernel_found = False

        for pkg, old, new in parsed:
            # Determine repo
            repo = "AUR"
            si = run_cmd(["pacman", "-Si", pkg])
            if si:
                m = re.search(r'^Repository\s*:\s*(.+)', si, re.M)
                if m: repo = m.group(1).strip()

            kernel = is_kernel(pkg)
            if kernel: kernel_found = True

            updates.append({"pkg": pkg, "old": old, "new": new, "repo": repo, "kernel": kernel})

        updates.sort(key=lambda x: (repo_order(x["repo"]), x["pkg"].lower()))

        def _done():
            self.updates = updates
            self.kernel_found = kernel_found
            self._show_updates()

        self.after(0, _done)

    def _show_up_to_date(self):
        self._set_status("System is up to date ✓",T["VER_NEW"])
        self.count_lbl.config(text="No updates available",fg=T["FG_DIM"])
        self.refresh_btn.enable()

    def _show_updates(self):
        for w in self.upd_rows.winfo_children(): w.destroy()
        for i,u in enumerate(self.updates):
            bg=T["KERNEL_BG"] if u["kernel"] else (T["BG_ROW_ALT"] if i%2==0 else T["BG_PANEL"])
            row=tk.Frame(self.upd_rows,bg=bg,pady=5); row.pack(fill="x")
            tk.Label(row,text=u["repo"],font=MONO_SB,bg=bg,fg=repo_color(u["repo"]),width=14,anchor="w").pack(side="left",padx=(20,4))
            tk.Label(row,text=u["pkg"],font=MONO_B if u["kernel"] else MONO,bg=bg,
                     fg=T["KERNEL_FG"] if u["kernel"] else T["FG"],width=30,anchor="w").pack(side="left",padx=(0,4))
            self._ver_label(row,bg,u["old"],u["new"],T["VER_OLD"])
            tk.Label(row,text="→",font=MONO,bg=bg,fg=T["FG_DIM"]).pack(side="left",padx=6)
            self._ver_label(row,bg,u["new"],u["old"],T["VER_NEW"])
            if u["kernel"]:
                tk.Label(row,text="⚠ KERNEL",font=MONO_SB,bg=bg,fg=T["KERNEL_FG"]).pack(side="left",padx=(12,0))
        c=len(self.updates)
        self.count_lbl.config(text=f"{c} package{'s' if c!=1 else ''} to update"+("  ⚠ kernel update!" if self.kernel_found else ""),fg=T["FG_DIM"])
        self._set_status("Ready",T["VER_NEW"]); self.update_btn.enable(); self.refresh_btn.enable()

    def _ver_label(self, parent, bg, ver, other, diff_col):
        prefix,suffix=split_ver_diff(ver,other)
        f=tk.Frame(parent,bg=bg); f.pack(side="left")
        if prefix: tk.Label(f,text=prefix,font=MONO,bg=bg,fg=T["FG"]).pack(side="left")
        if suffix: tk.Label(f,text=suffix,font=MONO_B,bg=bg,fg=diff_col).pack(side="left")

    def _run_sync(self):
        if self._sudo_pw and verify_sudo(self._sudo_pw):
            pw = self._sudo_pw
        else:
            dlg = SudoDialog(self, "Enter your sudo password to sync databases:")
            self.wait_window(dlg)
            if dlg.result is None: return
            if not verify_sudo(dlg.result):
                dlg2 = SudoDialog(self, "Enter your sudo password to sync databases:")
                dlg2.show_error("Incorrect password. Please try again.")
                self.wait_window(dlg2)
                if not dlg2.result or not verify_sudo(dlg2.result): return
                pw = dlg2.result
            else:
                pw = dlg.result
        self._sudo_pw = pw
        self.sync_btn.disable(); self.refresh_btn.disable(); self.update_btn.disable()
        self._show_log(); self._log_clear()
        self._log_line("Syncing package databases (pacman -Sy)...", T["ACCENT"])
        threading.Thread(target=self._do_sync, daemon=True).start()

    def _do_sync(self):
        self._stream_sudo(["pacman", "-Sy"])
        self._log_line("✓ Sync complete.", T["VER_NEW"])
        self.after(0, self.sync_btn.enable)
        self.after(0, self.refresh_btn.enable)
        self.after(200, self._check_updates)

    def _run_updates(self):
        if not self.updates: return
        # Collect the sudo password on the main thread (avoids deadlock from
        # blocking done.wait() while the Tk event loop also needs the main thread)
        if self._sudo_pw and verify_sudo(self._sudo_pw):
            pw = self._sudo_pw
        else:
            dlg = SudoDialog(self, "Enter your sudo password to begin updating:")
            self.wait_window(dlg)
            if dlg.result is None: return
            if not verify_sudo(dlg.result):
                dlg2 = SudoDialog(self, "Enter your sudo password to begin updating:")
                dlg2.show_error("Incorrect password. Please try again.")
                self.wait_window(dlg2)
                if not dlg2.result or not verify_sudo(dlg2.result): return
                pw = dlg2.result
            else:
                pw = dlg.result
        self._sudo_pw = pw
        self.update_btn.disable(); self.refresh_btn.disable()
        self._show_log(); self._log_clear()
        threading.Thread(target=self._do_updates,daemon=True).start()

    def _do_updates(self):
        has_off=any(u["repo"].lower() in ("core","extra","multilib") for u in self.updates)
        has_aur=any(u["repo"].lower() in ("chaotic-aur","aur") for u in self.updates)
        if has_off:
            self._log_line("── Official repo updates ──────────────────",T["FG_DIM"])
            self._stream_sudo(["pacman","-Syu","--noconfirm"])
        if has_aur and self.aur_helper:
            self._log_line("── AUR / chaotic-aur updates ──────────────",T["FG_DIM"])
            self._stream_cmd([self.aur_helper,"-Sua","--noconfirm"])
        self._log_line("✓ All updates complete.",T["VER_NEW"])
        if self.kernel_found:
            self._log_line("⚠  Kernel updated — reboot required!",T["KERNEL_FG"])
            self.after(0,self._prompt_reboot)
        else:
            self.after(0,self.refresh_btn.enable)
            self.after(600,self._check_updates)

    # ══════════════════════════════════════════════════════════════════════════
    # SEARCH & INSTALL TAB
    # ══════════════════════════════════════════════════════════════════════════
    def _build_search_page(self):
        page=self._tw(tk.Frame(self.page_container,bg=T["BG"]),bg="BG")
        self._pages["Search & Install"]=page
        sb=self._tw(tk.Frame(page,bg=T["BG"],pady=14),bg="BG"); sb.pack(fill="x",padx=24)
        self._tw(tk.Label(sb,text="Search packages:",font=MONO_B,bg=T["BG"],fg=T["FG"]),bg="BG",fg="FG").pack(side="left",padx=(0,10))
        ew=self._tw(tk.Frame(sb,bg=T["BG_INPUT"],highlightthickness=1,
                             highlightbackground=T["BORDER"],highlightcolor=T["ACCENT"]),
                   bg="BG_INPUT",highlightbackground="BORDER",highlightcolor="ACCENT")
        ew.pack(side="left",padx=(0,10))
        self.search_var=tk.StringVar()
        self.search_entry=tk.Entry(ew,textvariable=self.search_var,font=MONO,
                                   bg=T["BG_INPUT"],fg=T["FG"],insertbackground=T["FG"],
                                   relief="flat",bd=0,width=34)
        self._tw(self.search_entry,bg="BG_INPUT",fg="FG",insertbackground="FG")
        self.search_entry.pack(side="left",ipady=6,padx=(6,0))
        self.search_entry.bind("<Return>",lambda e:self._do_search())
        self.clear_btn=tk.Label(ew,text=" ✕ ",font=("Monospace",9),bg=T["BG_INPUT"],fg=T["FG_DIM"],cursor="hand2",padx=2)
        self._tw(self.clear_btn,bg="BG_INPUT",fg="FG_DIM")
        self.clear_btn.bind("<Button-1>",lambda e:self._clear_search())
        self.clear_btn.bind("<Enter>",lambda e:self.clear_btn.config(fg=T["VER_OLD"]))
        self.clear_btn.bind("<Leave>",lambda e:self.clear_btn.config(fg=T["FG_DIM"]))
        self.search_var.trace_add("write",self._on_search_var_change)
        self.search_btn=_make_btn(sb,"  Search  ",self._do_search,"BTN_ACCENT","BTN_ACCT_H","#ffffff")
        self.search_btn.pack(side="left",padx=(0,6)); self._tw(self.search_btn)
        self.search_status=self._tw(tk.Label(sb,text="",font=MONO_S,bg=T["BG"],fg=T["FG_DIM"]),bg="BG",fg="FG_DIM")
        self.search_status.pack(side="left",padx=(10,0))
        sf=self._tw(tk.Frame(sb,bg=T["BG"]),bg="BG"); sf.pack(side="right")
        self.selall_btn=_make_btn(sf,"☑ All",self._select_all,"BTN_BG","BTN_HOVER",state="disabled")
        self.selall_btn.pack(side="left",padx=(0,4)); self._tw(self.selall_btn)
        self.clrall_btn=_make_btn(sf,"☐ None",self._clear_all,"BTN_BG","BTN_HOVER",state="disabled")
        self.clrall_btn.pack(side="left"); self._tw(self.clrall_btn)
        self._tw(tk.Frame(page,bg=T["BORDER"],height=1),bg="BORDER").pack(fill="x")
        ro=self._tw(tk.Frame(page,bg=T["BG_PANEL"]),bg="BG_PANEL"); ro.pack(fill="both",expand=True)
        hdr=self._tw(tk.Frame(ro,bg=T["BG_HDR"],pady=6),bg="BG_HDR"); hdr.pack(fill="x")
        self._tw(tk.Label(hdr,text="",bg=T["BG_HDR"],width=3),bg="BG_HDR").pack(side="left",padx=(14,0))
        for i,(l,w) in enumerate([("Repo",13),("Package",26),("Version",18),("Description",50)]):
            self._tw(tk.Label(hdr,text=l,font=MONO_SB,bg=T["BG_HDR"],fg=T["FG_DIM"],width=w,anchor="w"),
                     bg="BG_HDR",fg="FG_DIM").pack(side="left",padx=(8 if i==0 else 4,0))
        self.src_canvas=self._tw(tk.Canvas(ro,bg=T["BG_PANEL"],highlightthickness=0,bd=0),bg="BG_PANEL")
        ssb=ttk.Scrollbar(ro,orient="vertical",command=self.src_canvas.yview)
        self.src_canvas.configure(yscrollcommand=ssb.set)
        ssb.pack(side="right",fill="y"); self.src_canvas.pack(side="left",fill="both",expand=True)
        self.src_rows=self._tw(tk.Frame(self.src_canvas,bg=T["BG_PANEL"]),bg="BG_PANEL")
        self.src_win=self.src_canvas.create_window((0,0),window=self.src_rows,anchor="nw")
        self.src_rows.bind("<Configure>",lambda e:self.src_canvas.configure(scrollregion=self.src_canvas.bbox("all")))
        self.src_canvas.bind("<Configure>",lambda e:self.src_canvas.itemconfig(self.src_win,width=e.width))
        self._tw(tk.Frame(page,bg=T["BORDER"],height=1),bg="BORDER").pack(fill="x")
        ab=self._tw(tk.Frame(page,bg=T["BG"],pady=10),bg="BG"); ab.pack(fill="x",padx=24)
        self.selection_lbl=self._tw(tk.Label(ab,text="No packages selected",font=MONO,bg=T["BG"],fg=T["FG_DIM"]),bg="BG",fg="FG_DIM")
        self.selection_lbl.pack(side="left")
        bg2=self._tw(tk.Frame(ab,bg=T["BG"]),bg="BG"); bg2.pack(side="right")
        self.uninstall_btn=_make_btn(bg2,"  ✕ Uninstall Selected  ",self._uninstall_selected,"BTN_RED","BTN_RED_H","#ffffff",state="disabled")
        self.uninstall_btn.pack(side="left",padx=(0,8)); self._tw(self.uninstall_btn)
        self.install_btn=_make_btn(bg2,"  ▶ Install Selected  ",self._install_selected,"BTN_GREEN","BTN_GREEN_H","#ffffff",state="disabled")
        self.install_btn.pack(side="left"); self._tw(self.install_btn)
        self._search_results=[]; self._check_vars=[]; self._check_boxes=[]; self._src_row_frames=[]

    def _on_search_var_change(self,*_):
        if self.search_var.get(): self.clear_btn.pack(side="left",padx=(0,4))
        else: self.clear_btn.pack_forget()

    def _clear_search(self):
        self.search_var.set("")
        for w in self.src_rows.winfo_children(): w.destroy()
        self._search_results=[]; self._check_vars=[]; self._check_boxes=[]; self._src_row_frames=[]
        self.search_status.config(text=""); self.selall_btn.disable(); self.clrall_btn.disable()
        self._update_action_bar(); self.search_entry.focus_set()

    def _make_checkbox(self, parent, var, bg_key, on_toggle):
        S=16
        c=tk.Canvas(parent,width=S,height=S,bg=T[bg_key],highlightthickness=0,bd=0,cursor="hand2")
        c._bg_key=bg_key
        def _draw():
            c.delete("all"); bg=T[c._bg_key]; c.config(bg=bg)
            if var.get():
                c.create_rectangle(0,0,S-1,S-1,outline=T["ACCENT"],fill=T["BTN_ACCENT"],width=1)
                c.create_line(3,8,6,12,fill="#ffffff",width=2)
                c.create_line(6,12,13,4,fill="#ffffff",width=2)
            else:
                c.create_rectangle(0,0,S-1,S-1,outline=T["BORDER"],fill=T["BG_INPUT"],width=1)
        def _toggle(e): var.set(not var.get()); _draw(); on_toggle()
        c.bind("<Button-1>",_toggle); c._redraw=_draw; _draw()
        return c

    def _do_search(self):
        query=self.search_var.get().strip()
        if not query: return
        self.search_btn.disable(); self.selall_btn.disable(); self.clrall_btn.disable()
        self.search_status.config(text="Searching…",fg=T["ACCENT"])
        for w in self.src_rows.winfo_children(): w.destroy()
        self._search_results=[]; self._check_vars=[]; self._check_boxes=[]; self._src_row_frames=[]
        self._update_action_bar()
        threading.Thread(target=self._fetch_search,args=(query,),daemon=True).start()

    def _fetch_search(self, query):
        results,seen=[],set()
        def parse_ss(text,source):
            lines=text.splitlines(); i=0
            while i<len(lines):
                line=lines[i].rstrip()
                if line and not line.startswith(" ") and "/" in line:
                    m=re.match(r'^([^/]+)/(\S+)\s+(\S+)(.*)',line)
                    if m:
                        repo,pkg,ver=m.group(1),m.group(2),m.group(3)
                        desc=lines[i+1].strip() if i+1<len(lines) else ""
                        installed="[installed]" in m.group(4)
                        if pkg not in seen:
                            seen.add(pkg)
                            results.append({"repo":repo,"pkg":pkg,"ver":ver,
                                            "desc":desc,"installed":installed,"source":source})
                    i+=2
                else: i+=1
        r1=subprocess.run(["pacman","-Ss",query],capture_output=True,text=True,timeout=30)
        parse_ss(r1.stdout,"pacman")
        if self.aur_helper:
            r2=subprocess.run([self.aur_helper,"-Ss","--aur",query],capture_output=True,text=True,timeout=60)
            parse_ss(r2.stdout,"aur")
        results.sort(key=lambda x:(repo_order(x["repo"]),x["pkg"].lower()))
        self._search_results=results; self.after(0,self._show_search_results)

    def _show_search_results(self):
        for w in self.src_rows.winfo_children(): w.destroy()
        self._check_vars=[]; self._check_boxes=[]; self._src_row_frames=[]
        if not self._search_results:
            self._tw(tk.Label(self.src_rows,text="No packages found.",font=MONO,bg=T["BG_PANEL"],fg=T["FG_DIM"]),
                     bg="BG_PANEL",fg="FG_DIM").pack(pady=30)
            self.search_status.config(text="No results",fg=T["FG_DIM"]); self.search_btn.enable(); return
        n=len(self._search_results)
        self.search_status.config(text=f"{n} result{'s' if n!=1 else ''}",fg=T["VER_NEW"])
        for i,r in enumerate(self._search_results):
            bk="BG_ROW_ALT" if i%2==0 else "BG_PANEL"
            var=tk.BooleanVar(value=False); self._check_vars.append(var)
            row=tk.Frame(self.src_rows,bg=T[bk],pady=4,cursor="hand2"); row.pack(fill="x")
            self._src_row_frames.append((row,bk))
            cb=self._make_checkbox(row,var,bk,self._update_action_bar)
            cb.pack(side="left",padx=(14,6),pady=2); self._check_boxes.append(cb)
            tk.Label(row,text=r["repo"],font=MONO_SB,bg=T[bk],fg=repo_color(r["repo"]),width=13,anchor="w").pack(side="left",padx=(0,4))
            sfx="  ✓" if r["installed"] else ""
            tk.Label(row,text=r["pkg"]+sfx,font=MONO,bg=T[bk],fg=T["VER_NEW"] if r["installed"] else T["FG"],width=26,anchor="w").pack(side="left",padx=(0,4))
            tk.Label(row,text=r["ver"],font=MONO,bg=T[bk],fg=T["FG_DIM"],width=18,anchor="w").pack(side="left",padx=(0,4))
            desc=r["desc"][:78]+("…" if len(r["desc"])>78 else "")
            tk.Label(row,text=desc,font=MONO_S,bg=T[bk],fg=T["FG_DIM"],anchor="w").pack(side="left",padx=(0,10),fill="x",expand=True)
            def _rc(e,v=var,c=cb): v.set(not v.get()); c._redraw(); self._update_action_bar()
            for ch in [row]+list(row.winfo_children()):
                if ch is not cb: ch.bind("<Button-1>",_rc)
        self.search_btn.enable(); self.selall_btn.enable(); self.clrall_btn.enable()
        self._update_action_bar()

    def _select_all(self):
        for v,cb in zip(self._check_vars,self._check_boxes): v.set(True); cb._redraw()
        self._update_action_bar()

    def _clear_all(self):
        for v,cb in zip(self._check_vars,self._check_boxes): v.set(False); cb._redraw()
        self._update_action_bar()

    def _get_checked(self):
        return [r for r,v in zip(self._search_results,self._check_vars) if v.get()]

    def _update_action_bar(self):
        checked=self._get_checked()
        to_inst=[r for r in checked if not r["installed"]]
        to_rem =[r for r in checked if r["installed"]]
        if not checked:
            self.selection_lbl.config(text="No packages selected",fg=T["FG_DIM"])
            self.install_btn.disable(); self.uninstall_btn.disable(); return
        parts=[]
        if to_inst:  parts.append(f"{len(to_inst)} to install")
        if to_rem:   parts.append(f"{len(to_rem)} to uninstall")
        self.selection_lbl.config(text="Selected: "+"  •  ".join(parts),fg=T["ACCENT"])
        if to_inst: self.install_btn.enable()
        else:       self.install_btn.disable()
        if to_rem:  self.uninstall_btn.enable()
        else:       self.uninstall_btn.disable()

    def _install_selected(self):
        to_inst=[r for r in self._get_checked() if not r["installed"]]
        if not to_inst: return
        prompt=f"Enter your sudo password to install:\n{', '.join(r['pkg'] for r in to_inst)}"
        if self._sudo_pw and verify_sudo(self._sudo_pw):
            pw=self._sudo_pw
        else:
            dlg=SudoDialog(self,prompt); self.wait_window(dlg)
            if dlg.result is None: return
            if not verify_sudo(dlg.result):
                dlg2=SudoDialog(self,prompt); dlg2.show_error("Incorrect password. Please try again.")
                self.wait_window(dlg2)
                if not dlg2.result or not verify_sudo(dlg2.result): return
                pw=dlg2.result
            else:
                pw=dlg.result
        self._sudo_pw=pw; self.install_btn.disable(); self.uninstall_btn.disable()
        self._show_log(); self._log_clear()
        self._log_line(f"Installing {len(to_inst)} package(s)…",T["ACCENT"])
        threading.Thread(target=self._do_install,args=(to_inst,),daemon=True).start()

    def _do_install(self, pkgs):
        off=[r for r in pkgs if r["source"]!="aur"]
        aur=[r for r in pkgs if r["source"]=="aur"]
        if off:
            self._log_line(f"pacman -S {' '.join(r['pkg'] for r in off)}",T["FG_DIM"])
            self._stream_sudo(["pacman","-S","--noconfirm"]+[r["pkg"] for r in off])
        if aur and self.aur_helper:
            self._log_line(f"{self.aur_helper} -S {' '.join(r['pkg'] for r in aur)}",T["FG_DIM"])
            self._stream_cmd([self.aur_helper,"-S","--noconfirm"]+[r["pkg"] for r in aur])
        self._log_line("✓ Install complete.",T["VER_NEW"])
        q=self.search_var.get().strip()
        if q: self.after(200,lambda:threading.Thread(target=self._fetch_search,args=(q,),daemon=True).start())
        self.after(0,self._update_action_bar)

    def _uninstall_selected(self):
        to_rem=[r for r in self._get_checked() if r["installed"]]
        if not to_rem: return
        names=[r["pkg"] for r in to_rem]
        if not messagebox.askyesno("Confirm Uninstall",
                                   f"Remove {len(names)} package(s)?\n\n"+"\n".join(f"  • {n}" for n in names),
                                   parent=self): return
        prompt=f"Enter your sudo password to remove:\n{', '.join(names)}"
        if self._sudo_pw and verify_sudo(self._sudo_pw):
            pw=self._sudo_pw
        else:
            dlg=SudoDialog(self,prompt); self.wait_window(dlg)
            if dlg.result is None: return
            if not verify_sudo(dlg.result):
                dlg2=SudoDialog(self,prompt); dlg2.show_error("Incorrect password. Please try again.")
                self.wait_window(dlg2)
                if not dlg2.result or not verify_sudo(dlg2.result): return
                pw=dlg2.result
            else:
                pw=dlg.result
        self._sudo_pw=pw; self.install_btn.disable(); self.uninstall_btn.disable()
        self._show_log(); self._log_clear()
        self._log_line(f"Removing {len(names)} package(s)…",T["VER_OLD"])
        threading.Thread(target=self._do_uninstall,args=(names,),daemon=True).start()

    def _do_uninstall(self, names):
        self._log_line(f"pacman -Rns {' '.join(names)}",T["FG_DIM"])
        self._stream_sudo(["pacman","-Rns","--noconfirm"]+names)
        self._log_line("✓ Removal complete.",T["VER_NEW"])
        q=self.search_var.get().strip()
        if q: self.after(200,lambda:threading.Thread(target=self._fetch_search,args=(q,),daemon=True).start())

    # ══════════════════════════════════════════════════════════════════════════
    # PACKAGE INFO TAB
    # ══════════════════════════════════════════════════════════════════════════
    def _build_info_page(self):
        page=self._tw(tk.Frame(self.page_container,bg=T["BG"]),bg="BG")
        self._pages["Package Info"]=page

        # Search bar
        sb=self._tw(tk.Frame(page,bg=T["BG"],pady=14),bg="BG"); sb.pack(fill="x",padx=24)
        self._tw(tk.Label(sb,text="Package name:",font=MONO_B,bg=T["BG"],fg=T["FG"]),bg="BG",fg="FG").pack(side="left",padx=(0,10))
        iw=self._tw(tk.Frame(sb,bg=T["BG_INPUT"],highlightthickness=1,
                             highlightbackground=T["BORDER"],highlightcolor=T["ACCENT"]),
                   bg="BG_INPUT",highlightbackground="BORDER",highlightcolor="ACCENT")
        iw.pack(side="left",padx=(0,10))
        self.info_var=tk.StringVar()
        ie=tk.Entry(iw,textvariable=self.info_var,font=MONO,bg=T["BG_INPUT"],fg=T["FG"],
                    insertbackground=T["FG"],relief="flat",bd=0,width=30)
        self._tw(ie,bg="BG_INPUT",fg="FG",insertbackground="FG")
        ie.pack(side="left",ipady=6,padx=(6,6))
        ie.bind("<Return>",lambda e:self._do_pkg_info())
        self.info_btn=_make_btn(sb,"  Look Up  ",self._do_pkg_info,"BTN_ACCENT","BTN_ACCT_H","#ffffff")
        self.info_btn.pack(side="left"); self._tw(self.info_btn)
        self.info_status=self._tw(tk.Label(sb,text="",font=MONO_S,bg=T["BG"],fg=T["FG_DIM"]),bg="BG",fg="FG_DIM")
        self.info_status.pack(side="left",padx=(12,0))

        self._tw(tk.Frame(page,bg=T["BORDER"],height=1),bg="BORDER").pack(fill="x")

        # Content area — left panel + right files list
        content=self._tw(tk.Frame(page,bg=T["BG"]),bg="BG")
        content.pack(fill="both",expand=True)

        # Left: scrollable info fields
        left=self._tw(tk.Frame(content,bg=T["BG_PANEL"]),bg="BG_PANEL")
        left.pack(side="left",fill="both",expand=True)
        self.info_canvas=self._tw(tk.Canvas(left,bg=T["BG_PANEL"],highlightthickness=0,bd=0),bg="BG_PANEL")
        isb=ttk.Scrollbar(left,orient="vertical",command=self.info_canvas.yview)
        self.info_canvas.configure(yscrollcommand=isb.set)
        isb.pack(side="right",fill="y"); self.info_canvas.pack(fill="both",expand=True)
        self.info_frame=self._tw(tk.Frame(self.info_canvas,bg=T["BG_PANEL"]),bg="BG_PANEL")
        self.info_win=self.info_canvas.create_window((0,0),window=self.info_frame,anchor="nw")
        self.info_frame.bind("<Configure>",lambda e:self.info_canvas.configure(scrollregion=self.info_canvas.bbox("all")))
        self.info_canvas.bind("<Configure>",lambda e:self.info_canvas.itemconfig(self.info_win,width=e.width))

        # Right: file list
        self._tw(tk.Frame(content,bg=T["BORDER"],width=1),bg="BORDER").pack(side="left",fill="y")
        right=self._tw(tk.Frame(content,bg=T["BG_PANEL"],width=320),bg="BG_PANEL")
        right.pack(side="left",fill="y")
        right.pack_propagate(False)
        self._tw(tk.Label(right,text="Installed Files",font=MONO_SB,bg=T["BG_HDR"],fg=T["FG_DIM"],anchor="w",pady=8),
                 bg="BG_HDR",fg="FG_DIM").pack(fill="x",padx=12)
        self.files_text=tk.Text(right,font=("Monospace",8),bg=T["BG_PANEL"],fg=T["FG_DIM"],
                                relief="flat",bd=0,state="disabled",wrap="none",padx=10)
        self._tw(self.files_text,bg="BG_PANEL",fg="FG_DIM")
        fsb=ttk.Scrollbar(right,command=self.files_text.yview)
        self.files_text.configure(yscrollcommand=fsb.set)
        fsb.pack(side="right",fill="y"); self.files_text.pack(fill="both",expand=True,pady=(4,0))

    def _do_pkg_info(self):
        pkg=self.info_var.get().strip()
        if not pkg: return
        self.info_btn.disable()
        self.info_status.config(text="Looking up…",fg=T["ACCENT"])
        for w in self.info_frame.winfo_children(): w.destroy()
        self.files_text.config(state="normal"); self.files_text.delete("1.0","end"); self.files_text.config(state="disabled")
        threading.Thread(target=self._fetch_pkg_info,args=(pkg,),daemon=True).start()

    def _fetch_pkg_info(self, pkg):
        # Try local first, then sync db
        local=run_cmd(["pacman","-Qi",pkg],timeout=10)
        sync =run_cmd(["pacman","-Si",pkg],timeout=10)
        raw  = local or sync
        files=run_cmd(["pacman","-Ql",pkg],timeout=10) if local else ""

        if not raw:
            # Try AUR
            if self.aur_helper:
                raw=run_cmd([self.aur_helper,"-Si","--aur",pkg],timeout=20)

        info={}
        if raw:
            for line in raw.splitlines():
                m=re.match(r'^([^:]+?)\s*:\s*(.+)',line)
                if m:
                    key=m.group(1).strip(); val=m.group(2).strip()
                    if key not in info: info[key]=val
                elif info:
                    last=list(info.keys())[-1]
                    info[last]+=" "+line.strip()

        self.after(0,lambda:self._show_pkg_info(pkg,info,files,bool(local)))

    def _show_pkg_info(self, pkg, info, files, installed):
        for w in self.info_frame.winfo_children(): w.destroy()

        if not info:
            tk.Label(self.info_frame,text=f"Package '{pkg}' not found.",
                     font=MONO,bg=T["BG_PANEL"],fg=T["FG_DIM"]).pack(pady=30)
            self.info_status.config(text="Not found",fg=T["VER_OLD"])
            self.info_btn.enable(); return

        # Status badge
        badge_f=tk.Frame(self.info_frame,bg=T["BG_PANEL"]); badge_f.pack(fill="x",padx=20,pady=(14,4))
        badge_col=T["VER_NEW"] if installed else T["FG_DIM"]
        badge_txt="● Installed" if installed else "○ Not installed"
        tk.Label(badge_f,text=badge_txt,font=MONO_SB,bg=T["BG_PANEL"],fg=badge_col).pack(side="left")

        SHOW=[("Name","Name"),("Version","Version"),("Description","Description"),
              ("URL","URL"),("Licenses","Licenses"),("Repository","Repository"),
              ("Installed Size","Installed Size"),("Download Size","Download Size"),
              ("Packager","Packager"),("Build Date","Build Date"),
              ("Install Date","Install Date"),("Install Reason","Install Reason"),
              ("Depends On","Depends On"),("Optional Deps","Optional Deps"),
              ("Required By","Required By"),("Conflicts With","Conflicts With")]

        for label,key in SHOW:
            val=info.get(key,"") or info.get(label,"")
            if not val or val=="None": continue
            row=tk.Frame(self.info_frame,bg=T["BG_PANEL"],pady=3); row.pack(fill="x",padx=20)
            tk.Label(row,text=label+":",font=MONO_SB,bg=T["BG_PANEL"],fg=T["FG_DIM"],
                     width=18,anchor="nw").pack(side="left")
            # Long values wrap
            tk.Label(row,text=val,font=MONO,bg=T["BG_PANEL"],fg=T["FG"],
                     anchor="nw",justify="left",wraplength=480).pack(side="left",fill="x",expand=True)

        self.info_status.config(text=f"Found: {info.get('Name',pkg)}",fg=T["VER_NEW"])
        self.info_btn.enable()

        # Files list
        self.files_text.config(state="normal"); self.files_text.delete("1.0","end")
        if files:
            for line in files.splitlines():
                parts=line.split(None,1)
                path=parts[1] if len(parts)>1 else line
                self.files_text.insert("end",path+"\n")
        else:
            self.files_text.insert("end","(not installed — no file list available)")
        self.files_text.config(state="disabled")

    # ══════════════════════════════════════════════════════════════════════════
    # SYSTEM STATS TAB
    # ══════════════════════════════════════════════════════════════════════════
    def _build_stats_page(self):
        page=self._tw(tk.Frame(self.page_container,bg=T["BG"]),bg="BG")
        self._pages["System Stats"]=page

        top=self._tw(tk.Frame(page,bg=T["BG"],pady=10),bg="BG"); top.pack(fill="x",padx=24)
        self._tw(tk.Label(top,text="System Statistics",font=MONO_B,bg=T["BG"],fg=T["FG"]),bg="BG",fg="FG").pack(side="left")
        self.stats_refresh_btn=_make_btn(top,"↻  Refresh Stats",self._refresh_stats,"BTN_BG","BTN_HOVER")
        self.stats_refresh_btn.pack(side="right"); self._tw(self.stats_refresh_btn)
        self._tw(tk.Frame(page,bg=T["BORDER"],height=1),bg="BORDER").pack(fill="x")

        # Two-column grid of stat cards + chart canvas
        main=self._tw(tk.Frame(page,bg=T["BG"]),bg="BG"); main.pack(fill="both",expand=True,padx=16,pady=12)

        # Left column — stat cards
        self._stats_left=self._tw(tk.Frame(main,bg=T["BG"]),bg="BG")
        self._stats_left.pack(side="left",fill="both",expand=True,padx=(0,8))

        # Right column — pie chart canvas
        self._stats_right=self._tw(tk.Frame(main,bg=T["BG"]),bg="BG")
        self._stats_right.pack(side="left",fill="both",expand=True,padx=(8,0))

        self._stats_canvas=tk.Canvas(self._stats_right,bg=T["BG"],highlightthickness=0,bd=0)
        self._tw(self._stats_canvas,bg="BG")
        self._stats_canvas.pack(fill="both",expand=True)
        self._stats_canvas.bind("<Configure>",lambda e:self._draw_stats_charts())

        # Placeholder labels — will be populated by _refresh_stats
        self._stat_labels={}
        CARDS=[
            ("pkg_count",  "📦 Total Packages",     "—"),
            ("explicit",   "🔖 Explicitly Installed","—"),
            ("aur_count",  "🌐 AUR Packages",        "—"),
            ("orphans",    "👻 Orphan Packages",      "—"),
            ("disk_pkg",   "💾 Package Cache Size",   "—"),
            ("disk_root",  "🖥  Root Filesystem",      "—"),
            ("disk_home",  "🏠 Home Filesystem",       "—"),
            ("last_upd",   "🕐 Last System Update",   "—"),
            ("kernel_ver", "🐧 Running Kernel",        "—"),
            ("uptime",     "⏱  System Uptime",         "—"),
        ]
        for i,(key,label,init) in enumerate(CARDS):
            card=self._tw(tk.Frame(self._stats_left,bg=T["BG_PANEL"],pady=10,padx=14),bg="BG_PANEL")
            card.grid(row=i//2,column=i%2,sticky="nsew",padx=5,pady=5)
            self._stats_left.columnconfigure(0,weight=1); self._stats_left.columnconfigure(1,weight=1)
            self._tw(tk.Label(card,text=label,font=MONO_S,bg=T["BG_PANEL"],fg=T["FG_DIM"],anchor="w"),
                     bg="BG_PANEL",fg="FG_DIM").pack(fill="x")
            vl=self._tw(tk.Label(card,text=init,font=MONO_L,bg=T["BG_PANEL"],fg=T["FG"],anchor="w"),
                        bg="BG_PANEL",fg="FG")
            vl.pack(fill="x"); self._stat_labels[key]=vl

        self._chart_data={}  # populated by _refresh_stats

    def _refresh_stats(self):
        if not hasattr(self,"_stat_labels"): return
        threading.Thread(target=self._fetch_stats,daemon=True).start()

    def _fetch_stats(self):
        data={}

        # Package counts
        all_pkgs=run_cmd(["pacman","-Q"])
        pkg_lines=[l for l in all_pkgs.splitlines() if l.strip()]
        data["pkg_count"]=str(len(pkg_lines))

        exp=run_cmd(["pacman","-Qe"])
        data["explicit"]=str(len([l for l in exp.splitlines() if l.strip()]))

        if self.aur_helper:
            aur_out=run_cmd([self.aur_helper,"-Qm"])
            data["aur_count"]=str(len([l for l in aur_out.splitlines() if l.strip()]))
        else:
            data["aur_count"]="n/a"

        orph=run_cmd(["pacman","-Qdtq"])
        data["orphans"]=str(len([l for l in orph.splitlines() if l.strip()])) if orph else "0"

        # Cache size
        cache_dir="/var/cache/pacman/pkg"
        try:
            total=sum(os.path.getsize(os.path.join(cache_dir,f))
                      for f in os.listdir(cache_dir)
                      if os.path.isfile(os.path.join(cache_dir,f)))
            data["disk_pkg"]=fmt_bytes(total)
        except Exception:
            data["disk_pkg"]="n/a"

        # Disk usage
        def disk_info(path):
            try:
                st=os.statvfs(path)
                total=st.f_blocks*st.f_frsize
                free=st.f_bavail*st.f_frsize
                used=total-free
                pct=int(used/total*100) if total else 0
                return f"{fmt_bytes(used)} / {fmt_bytes(total)}  ({pct}%)", used, total
            except Exception:
                return "n/a",0,1

        root_txt,root_used,root_total=disk_info("/")
        home_path=os.path.expanduser("~")
        home_txt,home_used,home_total=disk_info(home_path)
        data["disk_root"]=root_txt; data["disk_home"]=home_txt

        # Chart data
        data["_chart_root"]=(root_used,root_total)
        data["_chart_home"]=(home_used,home_total)

        # Last update
        try:
            with open("/var/log/pacman.log") as f:
                lines=[l for l in f if "starting full system upgrade" in l.lower() or "upgraded " in l.lower()]
            if lines:
                last=lines[-1]
                m=re.match(r'\[(\d{4}-\d{2}-\d{2})',last)
                data["last_upd"]=m.group(1) if m else "Unknown"
            else:
                data["last_upd"]="No record"
        except Exception:
            data["last_upd"]="Unknown"

        # Kernel
        data["kernel_ver"]=run_cmd(["uname","-r"],timeout=5) or "Unknown"

        # Uptime
        try:
            with open("/proc/uptime") as f: secs=float(f.read().split()[0])
            d,rem=divmod(int(secs),86400); h,rem=divmod(rem,3600); m2=rem//60
            data["uptime"]=f"{d}d {h}h {m2}m" if d else f"{h}h {m2}m"
        except Exception:
            data["uptime"]="Unknown"

        self.after(0,lambda:self._show_stats(data))

    def _show_stats(self, data):
        mapping={"pkg_count":("pkg_count","FG"),"explicit":("explicit","VER_NEW"),
                 "aur_count":("aur_count","REPO_AUR"),"orphans":("orphans","VER_OLD" if data.get("orphans","0")!="0" else "FG"),
                 "disk_pkg":("disk_pkg","FG"),"disk_root":("disk_root","FG"),
                 "disk_home":("disk_home","FG"),"last_upd":("last_upd","FG"),
                 "kernel_ver":("kernel_ver","REPO_MULTI"),"uptime":("uptime","FG")}
        for key,(dkey,fgk) in mapping.items():
            if key in self._stat_labels:
                self._stat_labels[key].config(text=data.get(dkey,"—"),fg=T[fgk])
        self._chart_data=data
        self._draw_stats_charts()

    def _draw_stats_charts(self):
        if not hasattr(self,"_stats_canvas") or not self._chart_data: return
        c=self._stats_canvas; c.delete("all")
        W=c.winfo_width(); H=c.winfo_height()
        if W<10 or H<10: return

        bg=T["BG"]; c.config(bg=bg)
        COLORS=[T["CHART_1"],T["CHART_2"],T["CHART_3"],T["CHART_4"],T["CHART_5"]]

        def draw_donut(cx,cy,r,used,total,label,color):
            # Background ring
            c.create_arc(cx-r,cy-r,cx+r,cy+r,start=0,extent=359.9,
                         style="arc",outline=T["BORDER"],width=18)
            if total>0:
                extent=(used/total)*359.9
                c.create_arc(cx-r,cy-r,cx+r,cy+r,start=90,extent=-extent,
                             style="arc",outline=color,width=18)
            pct=int(used/total*100) if total else 0
            c.create_text(cx,cy,text=f"{pct}%",font=MONO_B,fill=T["FG"])
            c.create_text(cx,cy+r+20,text=label,font=MONO_S,fill=T["FG_DIM"])

        # Draw two donuts
        ru,rt=self._chart_data.get("_chart_root",(0,1))
        hu,ht=self._chart_data.get("_chart_home",(0,1))

        half=W//2
        r=min(half//2-30, H//2-50, 80)
        if r>20:
            draw_donut(half//2,   H//2-20, r, ru, rt, "Root /",     COLORS[0])
            draw_donut(half+half//2, H//2-20, r, hu, ht, "Home ~",  COLORS[1])

        # Package breakdown bar
        pkg_total=int(self._chart_data.get("pkg_count","0") or 0)
        aur_n=int(self._chart_data.get("aur_count","0") or 0) if self._chart_data.get("aur_count")!="n/a" else 0
        exp_n=int(self._chart_data.get("explicit","0") or 0)
        orph_n=int(self._chart_data.get("orphans","0") or 0)
        dep_n=max(0,pkg_total-exp_n)

        bar_y=H-70; bar_h=20; bar_x=30; bar_w=W-60
        if pkg_total>0 and bar_w>10:
            c.create_text(bar_x,bar_y-16,text="Package Breakdown",font=MONO_S,fill=T["FG_DIM"],anchor="w")
            segments=[("Explicit",exp_n,COLORS[0]),("Dependencies",dep_n,COLORS[1]),("Orphans",orph_n,COLORS[2])]
            x=bar_x
            for lbl,n,col in segments:
                w2=int(bar_w*(n/pkg_total)) if pkg_total else 0
                if w2>0:
                    c.create_rectangle(x,bar_y,x+w2,bar_y+bar_h,fill=col,outline="")
                    if w2>40:
                        c.create_text(x+w2//2,bar_y+bar_h//2,text=f"{lbl}\n{n}",
                                      font=("Monospace",7),fill="#ffffff",justify="center")
                    x+=w2
            # Legend
            lx=bar_x; ly=bar_y+bar_h+10
            for lbl,n,col in segments:
                c.create_rectangle(lx,ly,lx+10,ly+10,fill=col,outline="")
                c.create_text(lx+14,ly,text=f"{lbl}: {n}",font=MONO_S,fill=T["FG_DIM"],anchor="nw")
                lx+=max(120,len(lbl)*9+50)

    # ══════════════════════════════════════════════════════════════════════════
    # ORPHANS TAB
    # ══════════════════════════════════════════════════════════════════════════
    def _build_orphans_page(self):
        page=self._tw(tk.Frame(self.page_container,bg=T["BG"]),bg="BG")
        self._pages["Orphans"]=page

        top=self._tw(tk.Frame(page,bg=T["BG"],pady=12),bg="BG"); top.pack(fill="x",padx=24)
        self._tw(tk.Label(top,text="Orphan Packages",font=MONO_B,bg=T["BG"],fg=T["FG"]),bg="BG",fg="FG").pack(side="left")
        self.orph_count_lbl=self._tw(tk.Label(top,text="",font=MONO_S,bg=T["BG"],fg=T["FG_DIM"]),bg="BG",fg="FG_DIM")
        self.orph_count_lbl.pack(side="left",padx=(16,0))
        br=self._tw(tk.Frame(top,bg=T["BG"]),bg="BG"); br.pack(side="right")
        self.orph_scan_btn=_make_btn(br,"↻  Scan",self._scan_orphans,"BTN_BG","BTN_HOVER")
        self.orph_scan_btn.pack(side="left",padx=(0,8)); self._tw(self.orph_scan_btn)
        self.orph_rem_btn=_make_btn(br,"🗑  Remove Selected",self._remove_orphans,"BTN_RED","BTN_RED_H","#ffffff",state="disabled")
        self.orph_rem_btn.pack(side="left"); self._tw(self.orph_rem_btn)

        self._tw(tk.Frame(page,bg=T["BORDER"],height=1),bg="BORDER").pack(fill="x")
        info=self._tw(tk.Label(page,
                               text="ℹ  Orphans are packages installed as dependencies that are no longer required by any other package.\n"
                                    "   Review carefully before removing — some orphans may be intentionally standalone.",
                               font=MONO_S,bg=T["BG"],fg=T["FG_DIM"],anchor="w",justify="left"),
                      bg="BG",fg="FG_DIM")
        info.pack(fill="x",padx=24,pady=(8,4))
        self._tw(tk.Frame(page,bg=T["BORDER"],height=1),bg="BORDER").pack(fill="x")

        # Column header
        hdr=self._tw(tk.Frame(page,bg=T["BG_HDR"],pady=6),bg="BG_HDR"); hdr.pack(fill="x")
        self._tw(tk.Label(hdr,text="",bg=T["BG_HDR"],width=3),bg="BG_HDR").pack(side="left",padx=(14,0))
        for i,(l,w) in enumerate([("Package",28),("Version",20),("Description",60)]):
            self._tw(tk.Label(hdr,text=l,font=MONO_SB,bg=T["BG_HDR"],fg=T["FG_DIM"],width=w,anchor="w"),
                     bg="BG_HDR",fg="FG_DIM").pack(side="left",padx=(8 if i==0 else 4,0))

        # Scrollable list
        ro=self._tw(tk.Frame(page,bg=T["BG_PANEL"]),bg="BG_PANEL"); ro.pack(fill="both",expand=True)
        self.orph_canvas=self._tw(tk.Canvas(ro,bg=T["BG_PANEL"],highlightthickness=0,bd=0),bg="BG_PANEL")
        osb=ttk.Scrollbar(ro,orient="vertical",command=self.orph_canvas.yview)
        self.orph_canvas.configure(yscrollcommand=osb.set)
        osb.pack(side="right",fill="y"); self.orph_canvas.pack(side="left",fill="both",expand=True)
        self.orph_rows=self._tw(tk.Frame(self.orph_canvas,bg=T["BG_PANEL"]),bg="BG_PANEL")
        self.orph_win=self.orph_canvas.create_window((0,0),window=self.orph_rows,anchor="nw")
        self.orph_rows.bind("<Configure>",lambda e:self.orph_canvas.configure(scrollregion=self.orph_canvas.bbox("all")))
        self.orph_canvas.bind("<Configure>",lambda e:self.orph_canvas.itemconfig(self.orph_win,width=e.width))

        self._tw(tk.Frame(page,bg=T["BORDER"],height=1),bg="BORDER").pack(fill="x")
        self._orph_pkgs=[]; self._orph_vars=[]; self._orph_cbs=[]; self._orph_row_frames=[]

    def _scan_orphans(self):
        self.orph_scan_btn.disable(); self.orph_rem_btn.disable()
        self.orph_count_lbl.config(text="Scanning…",fg=T["ACCENT"])
        for w in self.orph_rows.winfo_children(): w.destroy()
        self._orph_pkgs=[]; self._orph_vars=[]; self._orph_cbs=[]; self._orph_row_frames=[]
        threading.Thread(target=self._fetch_orphans,daemon=True).start()

    def _fetch_orphans(self):
        raw=run_cmd(["pacman","-Qdtq"],timeout=15)
        pkgs=[l.strip() for l in raw.splitlines() if l.strip()] if raw else []
        info={}
        if pkgs:
            si=run_cmd(["pacman","-Qi"]+pkgs,timeout=20)
            cur_name=""
            for line in si.splitlines():
                m=re.match(r'^Name\s*:\s*(.+)',line)
                if m: cur_name=m.group(1).strip(); info[cur_name]={"ver":"","desc":""}
                m=re.match(r'^Version\s*:\s*(.+)',line)
                if m and cur_name: info[cur_name]["ver"]=m.group(1).strip()
                m=re.match(r'^Description\s*:\s*(.+)',line)
                if m and cur_name: info[cur_name]["desc"]=m.group(1).strip()
        self._orph_pkgs=pkgs
        self.after(0,lambda:self._show_orphans(pkgs,info))

    def _show_orphans(self, pkgs, info):
        for w in self.orph_rows.winfo_children(): w.destroy()
        self._orph_vars=[]; self._orph_cbs=[]; self._orph_row_frames=[]
        if not pkgs:
            tk.Label(self.orph_rows,text="✓  No orphan packages found.",
                     font=MONO,bg=T["BG_PANEL"],fg=T["VER_NEW"]).pack(pady=30)
            self.orph_count_lbl.config(text="None found",fg=T["VER_NEW"])
            self.orph_scan_btn.enable(); return
        self.orph_count_lbl.config(text=f"{len(pkgs)} orphan{'s' if len(pkgs)!=1 else ''} found",fg=T["VER_OLD"])
        for i,pkg in enumerate(pkgs):
            bk="BG_ROW_ALT" if i%2==0 else "BG_PANEL"
            var=tk.BooleanVar(value=False); self._orph_vars.append(var)
            row=tk.Frame(self.orph_rows,bg=T[bk],pady=4,cursor="hand2"); row.pack(fill="x")
            self._orph_row_frames.append((row,bk))
            cb=self._make_checkbox(row,var,bk,self._update_orph_bar)
            cb.pack(side="left",padx=(14,6),pady=2); self._orph_cbs.append(cb)
            pinfo=info.get(pkg,{})
            tk.Label(row,text=pkg,font=MONO,bg=T[bk],fg=T["VER_OLD"],width=28,anchor="w").pack(side="left",padx=(0,4))
            tk.Label(row,text=pinfo.get("ver",""),font=MONO,bg=T[bk],fg=T["FG_DIM"],width=20,anchor="w").pack(side="left",padx=(0,4))
            desc=pinfo.get("desc","")[:70]
            tk.Label(row,text=desc,font=MONO_S,bg=T[bk],fg=T["FG_DIM"],anchor="w").pack(side="left",padx=(0,10),fill="x",expand=True)
            def _rc(e,v=var,c=cb): v.set(not v.get()); c._redraw(); self._update_orph_bar()
            for ch in [row]+list(row.winfo_children()):
                if ch is not cb: ch.bind("<Button-1>",_rc)
        self.orph_scan_btn.enable()
        self._update_orph_bar()

    def _update_orph_bar(self):
        sel=[p for p,v in zip(self._orph_pkgs,self._orph_vars) if v.get()]
        if sel: self.orph_rem_btn.enable()
        else:   self.orph_rem_btn.disable()

    def _remove_orphans(self):
        sel=[p for p,v in zip(self._orph_pkgs,self._orph_vars) if v.get()]
        if not sel: return
        if not messagebox.askyesno("Remove Orphans",
                                   f"Permanently remove {len(sel)} orphan package(s)?\n\n"+"\n".join(f"  • {p}" for p in sel),
                                   parent=self): return
        prompt=f"Enter sudo password to remove orphans:\n{', '.join(sel)}"
        if self._sudo_pw and verify_sudo(self._sudo_pw):
            pw=self._sudo_pw
        else:
            dlg=SudoDialog(self,prompt); self.wait_window(dlg)
            if dlg.result is None: return
            if not verify_sudo(dlg.result):
                dlg2=SudoDialog(self,prompt); dlg2.show_error("Incorrect password. Please try again.")
                self.wait_window(dlg2)
                if not dlg2.result or not verify_sudo(dlg2.result): return
                pw=dlg2.result
            else:
                pw=dlg.result
        self._sudo_pw=pw; self.orph_rem_btn.disable(); self.orph_scan_btn.disable()
        self._show_log(); self._log_clear()
        self._log_line(f"Removing {len(sel)} orphan(s)…",T["VER_OLD"])
        threading.Thread(target=self._do_remove_orphans,args=(sel,),daemon=True).start()

    def _do_remove_orphans(self, pkgs):
        self._stream_sudo(["pacman","-Rns","--noconfirm"]+pkgs)
        self._log_line("✓ Orphan removal complete.",T["VER_NEW"])
        self.after(500,self._scan_orphans)

    # ══════════════════════════════════════════════════════════════════════════
    # REPOSITORIES TAB
    # ══════════════════════════════════════════════════════════════════════════
    def _build_repos_page(self):
        page=self._tw(tk.Frame(self.page_container,bg=T["BG"]),bg="BG")
        self._pages["Repositories"]=page
        top=self._tw(tk.Frame(page,bg=T["BG"],pady=12),bg="BG"); top.pack(fill="x",padx=24)
        self._tw(tk.Label(top,text="Configured Repositories",font=MONO_B,bg=T["BG"],fg=T["FG"]),bg="BG",fg="FG").pack(side="left")
        self.repo_dirty_lbl=self._tw(tk.Label(top,text="",font=MONO_S,bg=T["BG"],fg=T["BTN_ORANGE"]),bg="BG",fg="BTN_ORANGE")
        self.repo_dirty_lbl.pack(side="right",padx=(0,16))
        br=self._tw(tk.Frame(top,bg=T["BG"]),bg="BG"); br.pack(side="right")
        self.repo_add_btn=_make_btn(br,"＋  Add Repo",self._add_repo_dialog,"BTN_ACCENT","BTN_ACCT_H","#ffffff")
        self.repo_add_btn.pack(side="left",padx=(0,8)); self._tw(self.repo_add_btn)
        self.repo_save_btn=_make_btn(br,"💾  Save Changes",self._save_repo_changes,"BTN_GREEN","BTN_GREEN_H","#ffffff",state="disabled")
        self.repo_save_btn.pack(side="left"); self._tw(self.repo_save_btn)
        self._tw(tk.Frame(page,bg=T["BORDER"],height=1),bg="BORDER").pack(fill="x")
        hdr=self._tw(tk.Frame(page,bg=T["BG_HDR"],pady=6),bg="BG_HDR"); hdr.pack(fill="x")
        for i,(l,w) in enumerate([("Status",8),("Repository",24),("Include / Server",44)]):
            self._tw(tk.Label(hdr,text=l,font=MONO_SB,bg=T["BG_HDR"],fg=T["FG_DIM"],width=w,anchor="w"),
                     bg="BG_HDR",fg="FG_DIM").pack(side="left",padx=(20 if i==0 else 4,0))
        self._tw(tk.Label(hdr,text="Actions",font=MONO_SB,bg=T["BG_HDR"],fg=T["FG_DIM"]),
                 bg="BG_HDR",fg="FG_DIM").pack(side="right",padx=(0,20))
        ro=self._tw(tk.Frame(page,bg=T["BG_PANEL"]),bg="BG_PANEL"); ro.pack(fill="both",expand=True)
        self.repo_canvas=self._tw(tk.Canvas(ro,bg=T["BG_PANEL"],highlightthickness=0,bd=0),bg="BG_PANEL")
        rsb=ttk.Scrollbar(ro,orient="vertical",command=self.repo_canvas.yview)
        self.repo_canvas.configure(yscrollcommand=rsb.set)
        rsb.pack(side="right",fill="y"); self.repo_canvas.pack(side="left",fill="both",expand=True)
        self.repo_rows=self._tw(tk.Frame(self.repo_canvas,bg=T["BG_PANEL"]),bg="BG_PANEL")
        self.repo_win=self.repo_canvas.create_window((0,0),window=self.repo_rows,anchor="nw")
        self.repo_rows.bind("<Configure>",lambda e:self.repo_canvas.configure(scrollregion=self.repo_canvas.bbox("all")))
        self.repo_canvas.bind("<Configure>",lambda e:self.repo_canvas.itemconfig(self.repo_win,width=e.width))
        self._tw(tk.Frame(page,bg=T["BORDER"],height=1),bg="BORDER").pack(fill="x")
        self._tw(tk.Label(page,text="ℹ  Changes are written to /etc/pacman.conf and require sudo. A pacman -Sy will run after saving.",
                          font=MONO_S,bg=T["BG"],fg=T["FG_DIM"],anchor="w"),
                 bg="BG",fg="FG_DIM").pack(fill="x",padx=24,pady=8)
        self._repo_preamble=[]; self._repo_sections=[]; self._repo_dirty=False

    def _reload_repos_view(self):
        p,s=parse_pacman_conf()
        self._repo_preamble=p; self._repo_sections=s; self._repo_dirty=False
        self.repo_dirty_lbl.config(text=""); self.repo_save_btn.disable()
        self._render_repo_rows()

    def _render_repo_rows(self):
        for w in self.repo_rows.winfo_children(): w.destroy()
        for i,sec in enumerate(s for s in self._repo_sections if s["type"]=="repo"):
            bk="BG_ROW_ALT" if i%2==0 else "BG_PANEL"; bg=T[bk]
            row=tk.Frame(self.repo_rows,bg=bg,pady=7); row.pack(fill="x")
            en=sec["enabled"]
            tk.Label(row,text="● ON " if en else "○ OFF",font=MONO_SB,bg=bg,
                     fg=T["VER_NEW"] if en else T["FG_DIM"],width=8,anchor="w").pack(side="left",padx=(20,4))
            tk.Label(row,text=f"[{sec['name']}]",font=MONO_B,bg=bg,
                     fg=repo_color(sec["name"]),width=24,anchor="w").pack(side="left",padx=(0,4))
            incs=[ln.strip() for ln in sec["lines"][1:] if re.match(r'^#?\s*(Include|Server)\s*=',ln.strip())]
            inc_txt="  |  ".join(re.sub(r'^#?\s*','',x) for x in incs) or "(none)"
            tk.Label(row,text=inc_txt,font=MONO_S,bg=bg,fg=T["FG_DIM"],anchor="w").pack(side="left",padx=(0,10),fill="x",expand=True)
            af=tk.Frame(row,bg=bg); af.pack(side="right",padx=(0,16))
            if en: _make_btn(af," Disable ",lambda s=sec:self._toggle_repo(s,False),"BTN_ORANGE","BTN_ORNG_H","#ffffff").pack(side="left",padx=3)
            else:  _make_btn(af," Enable  ",lambda s=sec:self._toggle_repo(s,True),"BTN_GREEN","BTN_GREEN_H","#ffffff").pack(side="left",padx=3)
            if sec["name"].lower() not in ("core","extra","options"):
                _make_btn(af," Remove ",lambda s=sec:self._remove_repo(s),"BTN_RED","BTN_RED_H","#ffffff").pack(side="left",padx=3)

    def _mark_dirty(self):
        self._repo_dirty=True; self.repo_dirty_lbl.config(text="● Unsaved changes",fg=T["BTN_ORANGE"])
        self.repo_save_btn.enable()

    def _toggle_repo(self,sec,en): sec["enabled"]=en; self._mark_dirty(); self._render_repo_rows()

    def _remove_repo(self,sec):
        if not messagebox.askyesno("Remove Repository",f"Remove [{sec['name']}] from pacman.conf?",parent=self): return
        self._repo_sections=[s for s in self._repo_sections if s is not sec]
        self._mark_dirty(); self._render_repo_rows()

    def _add_repo_dialog(self):
        dlg=tk.Toplevel(self); dlg.title("Add Repository")
        dlg.configure(bg=T["BG"]); dlg.geometry("520x310")
        dlg.resizable(False,False); dlg.grab_set(); dlg.transient(self)
        tk.Label(dlg,text="Add Repository to pacman.conf",font=MONO_B,bg=T["BG"],fg=T["ACCENT"]).pack(pady=(20,4))
        tk.Label(dlg,text="Enter the repository name and its Include or Server line.",
                 font=MONO_S,bg=T["BG"],fg=T["FG_DIM"],justify="center").pack(pady=(0,14))
        def field(label):
            f=tk.Frame(dlg,bg=T["BG"]); f.pack(pady=4)
            tk.Label(f,text=label,font=MONO_S,bg=T["BG"],fg=T["FG"],width=18,anchor="e").pack(side="left",padx=(0,8))
            e=tk.Entry(f,font=MONO,bg=T["BG_INPUT"],fg=T["FG"],insertbackground=T["FG"],
                       relief="flat",bd=0,width=28,highlightthickness=1,
                       highlightcolor=T["ACCENT"],highlightbackground=T["BORDER"])
            e.pack(side="left",ipady=5,padx=2); return e
        ne=field("Repository name:"); se=field("Include / Server:")
        el=tk.Label(dlg,text="",font=MONO_S,bg=T["BG"],fg=T["VER_OLD"]); el.pack(pady=(4,0))
        def do_add():
            n=ne.get().strip().strip("[]"); s=se.get().strip()
            if not n: el.config(text="Repository name is required."); return
            if not s: el.config(text="Include or Server line is required."); return
            if any(x["name"].lower()==n.lower() for x in self._repo_sections):
                el.config(text=f"[{n}] already exists."); return
            sl=(s if re.match(r'^(Include|Server)\s*=',s) else f"Server = {s}")+"\n"
            self._repo_sections.append({"name":n,"enabled":True,"lines":[f"[{n}]\n",sl,"\n"],"type":"repo"})
            self._mark_dirty(); self._render_repo_rows(); dlg.destroy()
        br=tk.Frame(dlg,bg=T["BG"]); br.pack(pady=(12,0))
        _make_btn(br,"  Add Repository  ",do_add,"BTN_ACCENT","BTN_ACCT_H","#ffffff").pack(side="left",padx=(0,10))
        _make_btn(br,"  Cancel  ",dlg.destroy,"BTN_BG","BTN_HOVER").pack(side="left")
        ne.focus_set(); se.bind("<Return>",lambda e:do_add())

    def _save_repo_changes(self):
        # Collect the sudo password on the main thread (same fix as _run_updates)
        if self._sudo_pw and verify_sudo(self._sudo_pw):
            pw = self._sudo_pw
        else:
            dlg = SudoDialog(self, "Enter your sudo password to write /etc/pacman.conf:")
            self.wait_window(dlg)
            if dlg.result is None: return
            if not verify_sudo(dlg.result):
                dlg2 = SudoDialog(self, "Enter your sudo password to write /etc/pacman.conf:")
                dlg2.show_error("Incorrect password. Please try again.")
                self.wait_window(dlg2)
                if not dlg2.result or not verify_sudo(dlg2.result): return
                pw = dlg2.result
            else:
                pw = dlg.result
        self._sudo_pw=pw
        new_conf=write_pacman_conf(self._repo_preamble,self._repo_sections)
        self._show_log(); self._log_clear()
        self._log_line("Writing /etc/pacman.conf…",T["ACCENT"])
        def _write():
            proc=subprocess.Popen(["sudo","-S","-p","","tee",PACMAN_CONF],
                                  stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
            try: proc.stdin.write(self._sudo_pw+"\n"); proc.stdin.write(new_conf); proc.stdin.close()
            except BrokenPipeError: pass
            out,_=proc.communicate()
            if proc.returncode==0:
                self._log_line("✓ pacman.conf saved.",T["VER_NEW"])
                self._log_line("Syncing new repo databases…",T["ACCENT"])
                self._stream_sudo(["pacman","-Sy","--noconfirm"])
                self._log_line("✓ Done.",T["VER_NEW"])
                self.after(0,self._reload_repos_view)
            else: self._log_line(f"✗ Failed:\n{out}",T["VER_OLD"])
        threading.Thread(target=_write,daemon=True).start()


    # ══════════════════════════════════════════════════════════════════════════
    # MIRRORS TAB
    # ══════════════════════════════════════════════════════════════════════════
    REFLECTOR_CONF = "/etc/xdg/reflector/reflector.conf"

    def _build_mirrors_page(self):
        page=self._tw(tk.Frame(self.page_container,bg=T["BG"]),bg="BG")
        self._pages["Mirrors"]=page

        # Scrollable canvas
        outer=self._tw(tk.Frame(page,bg=T["BG_PANEL"]),bg="BG_PANEL")
        outer.pack(fill="both",expand=True)
        self.mir_canvas=self._tw(tk.Canvas(outer,bg=T["BG_PANEL"],highlightthickness=0,bd=0),bg="BG_PANEL")
        msb=ttk.Scrollbar(outer,orient="vertical",command=self.mir_canvas.yview)
        self.mir_canvas.configure(yscrollcommand=msb.set)
        msb.pack(side="right",fill="y"); self.mir_canvas.pack(side="left",fill="both",expand=True)
        inner=self._tw(tk.Frame(self.mir_canvas,bg=T["BG_PANEL"]),bg="BG_PANEL")
        mir_win=self.mir_canvas.create_window((0,0),window=inner,anchor="nw")
        inner.bind("<Configure>",lambda e:self.mir_canvas.configure(scrollregion=self.mir_canvas.bbox("all")))
        self.mir_canvas.bind("<Configure>",lambda e:self.mir_canvas.itemconfig(mir_win,width=e.width))

        def section(parent, title):
            self._tw(tk.Label(parent,text=title,font=MONO_SB,bg=T["BG_PANEL"],fg=T["ACCENT"],anchor="w"),
                     bg="BG_PANEL",fg="ACCENT").pack(fill="x",padx=24,pady=(18,4))
            self._tw(tk.Frame(parent,bg=T["BORDER"],height=1),bg="BORDER").pack(fill="x",padx=24)

        def row_frame(parent):
            f=self._tw(tk.Frame(parent,bg=T["BG_PANEL"]),bg="BG_PANEL")
            f.pack(fill="x",padx=32,pady=4)
            return f

        def lbl(parent, text, width=26):
            l=self._tw(tk.Label(parent,text=text,font=MONO,bg=T["BG_PANEL"],fg=T["FG"],
                                width=width,anchor="w"),bg="BG_PANEL",fg="FG")
            l.pack(side="left")
            return l

        def entry_box(parent, var, width=8, hint=""):
            """Bordered entry widget matching the search box style, with optional hint."""
            ew=self._tw(tk.Frame(parent,bg=T["BG_INPUT"],highlightthickness=1,
                                 highlightbackground=T["BORDER"],highlightcolor=T["ACCENT"]),
                        bg="BG_INPUT",highlightbackground="BORDER",highlightcolor="ACCENT")
            ew.pack(side="left",padx=(0,8))
            e=tk.Entry(ew,textvariable=var,font=MONO,bg=T["BG_INPUT"],fg=T["FG"],
                       insertbackground=T["FG"],relief="flat",bd=0,width=width)
            self._tw(e,bg="BG_INPUT",fg="FG")
            e.pack(side="left",ipady=5,padx=(6,6))
            if hint:
                self._tw(tk.Label(parent,text=hint,font=MONO_S,bg=T["BG_PANEL"],fg=T["FG_DIM"]),
                         bg="BG_PANEL",fg="FG_DIM").pack(side="left")

        # ── Country ──────────────────────────────────────────────────────────
        section(inner,"Country / Region")
        rf=row_frame(inner); lbl(rf,"Countries:")
        self.mir_country_var=tk.StringVar()
        entry_box(rf,self.mir_country_var,width=34,hint="e.g. US,GB,DE  (leave blank for all)")

        # ── Protocol ─────────────────────────────────────────────────────────
        section(inner,"Protocol")
        pf=row_frame(inner)
        self.mir_proto_https=tk.BooleanVar(value=True)
        self.mir_proto_http =tk.BooleanVar(value=False)
        for var,txt in [(self.mir_proto_https,"https"),(self.mir_proto_http,"http")]:
            cb=self._make_checkbox(pf,var,"BG_PANEL",lambda:None)
            cb.pack(side="left",padx=(0,4))
            self._tw(tk.Label(pf,text=txt,font=MONO,bg=T["BG_PANEL"],fg=T["FG"]),
                     bg="BG_PANEL",fg="FG").pack(side="left",padx=(0,18))

        # ── Sort ─────────────────────────────────────────────────────────────
        section(inner,"Sort By")
        sf2=row_frame(inner)
        self.mir_sort_var=tk.StringVar(value="rate")
        for val,txt in [("rate","Download Rate"),("score","Mirror Score"),
                        ("delay","Sync Delay"),("age","Last Sync Age"),("country","Country")]:
            rb=tk.Radiobutton(sf2,text=txt,variable=self.mir_sort_var,value=val,
                              font=MONO,bg=T["BG_PANEL"],fg=T["FG"],
                              selectcolor=T["BTN_ACCENT"],activebackground=T["BG_PANEL"],
                              activeforeground=T["FG"],relief="flat",bd=0,cursor="hand2")
            self._tw(rb,bg="BG_PANEL",fg="FG"); rb.pack(side="left",padx=(0,16))

        # ── Number of mirrors ────────────────────────────────────────────────
        section(inner,"Number of Mirrors")
        nf=row_frame(inner); lbl(nf,"Latest N mirrors:")
        self.mir_num_var=tk.StringVar(value="5")
        entry_box(nf,self.mir_num_var,width=5,hint="select from N most recently synced")

        # ── Age ──────────────────────────────────────────────────────────────
        section(inner,"Maximum Mirror Age")
        af2=row_frame(inner); lbl(af2,"Maximum age:")
        self.mir_age_var=tk.StringVar(value="12")
        entry_box(af2,self.mir_age_var,width=5,hint="hours since last sync")

        # ── Connection timeout ────────────────────────────────────────────────
        section(inner,"Connection Timeout")
        tf=row_frame(inner); lbl(tf,"Connection timeout:")
        self.mir_timeout_var=tk.StringVar(value="5")
        entry_box(tf,self.mir_timeout_var,width=5,hint="seconds")

        # ── Extra flags ───────────────────────────────────────────────────────
        section(inner,"Extra Options")
        ef2=row_frame(inner)
        self.mir_ipv4=tk.BooleanVar(value=False)
        self.mir_ipv6=tk.BooleanVar(value=False)
        self.mir_download_timeout_var=tk.StringVar(value="")
        for var,txt in [(self.mir_ipv4,"IPv4 only"),(self.mir_ipv6,"IPv6 only")]:
            cb=self._make_checkbox(ef2,var,"BG_PANEL",lambda:None)
            cb.pack(side="left",padx=(0,4))
            self._tw(tk.Label(ef2,text=txt,font=MONO,bg=T["BG_PANEL"],fg=T["FG"]),
                     bg="BG_PANEL",fg="FG").pack(side="left",padx=(0,18))

        # ── Status / info ─────────────────────────────────────────────────────
        self._tw(tk.Frame(inner,bg=T["BORDER"],height=1),bg="BORDER").pack(fill="x",padx=24,pady=(18,0))
        self.mir_status_lbl=self._tw(tk.Label(inner,text="",font=MONO_S,bg=T["BG_PANEL"],fg=T["FG_DIM"],anchor="w"),
                                     bg="BG_PANEL",fg="FG_DIM")
        self.mir_status_lbl.pack(fill="x",padx=24,pady=(6,0))

        # ── Bottom button bar ─────────────────────────────────────────────────
        self._tw(tk.Frame(page,bg=T["BORDER"],height=1),bg="BORDER").pack(fill="x")
        bot=self._tw(tk.Frame(page,bg=T["BG"],pady=10),bg="BG"); bot.pack(fill="x",padx=24)
        self.mir_dirty_lbl=self._tw(tk.Label(bot,text="",font=MONO_S,bg=T["BG"],fg=T["FG_DIM"]),
                                    bg="BG",fg="FG_DIM")
        self.mir_dirty_lbl.pack(side="left")
        br=self._tw(tk.Frame(bot,bg=T["BG"]),bg="BG"); br.pack(side="right")
        self.mir_save_btn=_make_btn(br,"  💾  Save Config  ",self._save_mirror_conf,"BTN_ACCENT","BTN_ACCT_H","#ffffff")
        self.mir_save_btn.pack(side="left",padx=(0,8)); self._tw(self.mir_save_btn)
        self.mir_run_btn=_make_btn(br,"  ▶  Run Reflector Now  ",self._run_reflector,"BTN_GREEN","BTN_GREEN_H","#ffffff")
        self.mir_run_btn.pack(side="left"); self._tw(self.mir_run_btn)

        # Watch for any changes to mark dirty
        for var in (self.mir_country_var,self.mir_proto_https,self.mir_proto_http,
                    self.mir_sort_var,self.mir_num_var,self.mir_age_var,
                    self.mir_timeout_var,self.mir_ipv4,self.mir_ipv6):
            var.trace_add("write",self._mir_mark_dirty)
        self._mir_dirty=False

    def _mir_mark_dirty(self, *_):
        self._mir_dirty=True
        self.mir_dirty_lbl.config(text="● Unsaved changes",fg=T["BTN_ORANGE"])

    def _load_mirror_conf(self):
        """Read reflector.conf and populate UI widgets."""
        path=self.REFLECTOR_CONF
        self._mir_dirty=False
        self.mir_dirty_lbl.config(text="")
        # Defaults
        self.mir_country_var.set("")
        self.mir_proto_https.set(True); self.mir_proto_http.set(False)
        self.mir_sort_var.set("rate")
        self.mir_num_var.set("5")
        self.mir_age_var.set("12")
        self.mir_timeout_var.set("5")
        self.mir_ipv4.set(False); self.mir_ipv6.set(False)
        try:
            with open(path) as f: lines=f.readlines()
        except (FileNotFoundError,PermissionError):
            self.mir_status_lbl.config(text=f"ℹ  {path} not found — showing defaults.",fg=T["FG_DIM"])
            return
        # Temporarily detach traces so loading doesn't mark dirty
        proto_https,proto_http=False,False
        for line in lines:
            line=line.strip()
            if not line or line.startswith("#"): continue
            if line.startswith("--country"):
                val=re.sub(r"^--country\s*","",line).strip()
                self.mir_country_var.set(val)
            elif line.startswith("--protocol"):
                val=re.sub(r"^--protocol\s*","",line).strip()
                proto_https="https" in val; proto_http="http" in val and "https" not in val
            elif line.startswith("--sort"):
                val=re.sub(r"^--sort\s*","",line).strip()
                self.mir_sort_var.set(val)
            elif line.startswith("--latest"):
                val=re.sub(r"^--latest\s*","",line).strip()
                if val: self.mir_num_var.set(val)
            elif line.startswith("--age"):
                val=re.sub(r"^--age\s*","",line).strip()
                if val: self.mir_age_var.set(val)
            elif line.startswith("--connection-timeout"):
                val=re.sub(r"^--connection-timeout\s*","",line).strip()
                if val: self.mir_timeout_var.set(val)
            elif line=="--ipv4": self.mir_ipv4.set(True)
            elif line=="--ipv6": self.mir_ipv6.set(True)
        self.mir_proto_https.set(proto_https or (not proto_http))
        self.mir_proto_http.set(proto_http)
        self._mir_dirty=False
        self.mir_dirty_lbl.config(text="")
        self.mir_status_lbl.config(text=f"✓  Loaded from {path}",fg=T["VER_NEW"])

    # Options this UI manages — any other lines in the conf are preserved as-is
    _MIR_MANAGED = ("--country","--protocol","--sort","--latest","--age",
                    "--connection-timeout","--ipv4","--ipv6")

    def _build_reflector_conf(self):
        """Merge UI-controlled options into the existing conf, preserving unmanaged lines."""
        NL = "\n"
        # Read existing file so unmanaged options (e.g. --save) are kept
        try:
            with open(self.REFLECTOR_CONF) as f:
                existing = f.readlines()
        except (FileNotFoundError, PermissionError):
            existing = []

        # Strip lines we manage (will be re-added below with current values)
        kept = []
        for line in existing:
            s = line.strip()
            if not s or s.startswith("#"):
                kept.append(line); continue
            if any(s == opt or s.startswith(opt + " ") for opt in self._MIR_MANAGED):
                continue  # will be replaced by UI values
            kept.append(line)

        # Build the managed section
        managed = []
        country = self.mir_country_var.get().strip()
        if country: managed.append("--country " + country + NL)
        protos = []
        if self.mir_proto_https.get(): protos.append("https")
        if self.mir_proto_http.get():  protos.append("http")
        if protos: managed.append("--protocol " + ",".join(protos) + NL)
        sort = self.mir_sort_var.get().strip()
        if sort: managed.append("--sort " + sort + NL)
        num = self.mir_num_var.get().strip()
        if num.isdigit(): managed.append("--latest " + num + NL)
        age = self.mir_age_var.get().strip()
        if age: managed.append("--age " + age + NL)
        timeout = self.mir_timeout_var.get().strip()
        if timeout: managed.append("--connection-timeout " + timeout + NL)
        if self.mir_ipv4.get(): managed.append("--ipv4" + NL)
        if self.mir_ipv6.get(): managed.append("--ipv6" + NL)

        return "".join(kept + managed)

    def _save_mirror_conf(self):
        path=self.REFLECTOR_CONF
        new_conf=self._build_reflector_conf()
        if self._sudo_pw and verify_sudo(self._sudo_pw):
            pw=self._sudo_pw
        else:
            dlg=SudoDialog(self,f"Enter your sudo password to write {path}:")
            self.wait_window(dlg)
            if dlg.result is None: return
            if not verify_sudo(dlg.result):
                dlg2=SudoDialog(self,f"Enter your sudo password to write {path}:")
                dlg2.show_error("Incorrect password. Please try again.")
                self.wait_window(dlg2)
                if not dlg2.result or not verify_sudo(dlg2.result): return
                pw=dlg2.result
            else:
                pw=dlg.result
        self._sudo_pw=pw
        self._show_log(); self._log_clear()
        self._log_line(f"Writing {path}…",T["ACCENT"])
        def _write():
            import tempfile, os
            # Write to a temp file first, then sudo cp — avoids password leaking into the target file
            try:
                with tempfile.NamedTemporaryFile(mode="w",suffix=".conf",delete=False) as tf:
                    tf.write(new_conf); tmp=tf.name
            except Exception as e:
                self._log_line(f"✗ Failed to create temp file: {e}",T["VER_OLD"]); return
            proc=run_sudo_cmd(self._sudo_pw,["cp",tmp,path])
            proc.wait()
            try: os.unlink(tmp)
            except Exception: pass
            if proc.returncode==0:
                self._log_line(f"✓ {path} saved.",T["VER_NEW"])
                self.after(0,lambda:self.mir_dirty_lbl.config(text=""))
                self.after(0,lambda:self.mir_status_lbl.config(text=f"✓  Saved to {path}",fg=T["VER_NEW"]))
                self._mir_dirty=False
            else:
                self._log_line("✗ Failed to write config.",T["VER_OLD"])
        threading.Thread(target=_write,daemon=True).start()

    def _run_reflector(self):
        if not shutil.which("reflector"):
            messagebox.showerror("Not Found","reflector is not installed.\nInstall it with: sudo pacman -S reflector",parent=self)
            return
        if self._sudo_pw and verify_sudo(self._sudo_pw):
            pw=self._sudo_pw
        else:
            dlg=SudoDialog(self,"Enter your sudo password to run reflector:")
            self.wait_window(dlg)
            if dlg.result is None: return
            if not verify_sudo(dlg.result):
                dlg2=SudoDialog(self,"Enter your sudo password to run reflector:")
                dlg2.show_error("Incorrect password. Please try again.")
                self.wait_window(dlg2)
                if not dlg2.result or not verify_sudo(dlg2.result): return
                pw=dlg2.result
            else:
                pw=dlg.result
        self._sudo_pw=pw
        self.mir_run_btn.disable(); self.mir_save_btn.disable()
        self._show_log(); self._log_clear()
        self._log_line("Running reflector — this may take a minute…",T["ACCENT"])
        def _run():
            # Build the reflector command by parsing the conf file options directly,
            # so we are not relying on reflector's --config flag (not all versions support it).
            # Always append --save to write the mirrorlist.
            cmd_args=["reflector"]
            try:
                with open(self.REFLECTOR_CONF) as f:
                    for line in f:
                        s=line.strip()
                        if s and not s.startswith("#"):
                            parts=s.split(None,1)
                            cmd_args.append(parts[0])
                            if len(parts)>1: cmd_args.append(parts[1])
            except (FileNotFoundError,PermissionError):
                self._log_line("Warning: could not read conf file — running with defaults.",T["VER_OLD"])
            if "--save" not in cmd_args:
                cmd_args+=["--save","/etc/pacman.d/mirrorlist"]
            self._log_line("Command: "+" ".join(cmd_args),T["FG_DIM"])
            self._stream_sudo(cmd_args)
            self._log_line("✓ Mirrorlist updated.",T["VER_NEW"])
            self.after(0,self.mir_run_btn.enable)
            self.after(0,self.mir_save_btn.enable)
            self.after(0,lambda:self.mir_status_lbl.config(
                text="✓  Reflector ran successfully — /etc/pacman.d/mirrorlist updated.",fg=T["VER_NEW"]))
        threading.Thread(target=_run,daemon=True).start()

    # ══════════════════════════════════════════════════════════════════════════
    # SHARED UTILITIES
    # ══════════════════════════════════════════════════════════════════════════
    def _prompt_sudo(self, prompt="Enter your sudo password:"):
        if self._sudo_pw and verify_sudo(self._sudo_pw): return self._sudo_pw
        result,done=[None],threading.Event()
        def _do():
            dlg=SudoDialog(self,prompt); self.wait_window(dlg)
            if dlg.result is None: done.set(); return
            if verify_sudo(dlg.result): result[0]=dlg.result; done.set(); return
            dlg2=SudoDialog(self,prompt); dlg2.show_error("Incorrect password. Please try again.")
            self.wait_window(dlg2)
            if dlg2.result and verify_sudo(dlg2.result): result[0]=dlg2.result
            done.set()
        self.after(0,_do); done.wait(); return result[0]

    def _stream_sudo(self, cmd):
        proc=run_sudo_cmd(self._sudo_pw,cmd)
        for line in proc.stdout: self._log_line(line.rstrip(),T["FG"])
        proc.wait()
        if proc.returncode not in (0,None): self._log_line(f"Exit code: {proc.returncode}",T["VER_OLD"])

    def _stream_cmd(self, cmd):
        try:
            proc=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1)
            for line in proc.stdout: self._log_line(line.rstrip(),T["FG"])
            proc.wait()
        except Exception as e: self._log_line(f"Error: {e}",T["VER_OLD"])

    def _set_status(self,msg,color=None): self.status_lbl.config(text=msg,fg=color or T["FG_DIM"])
    def _show_log(self): self.log_frame.pack(fill="x")
    def _hide_log(self): self.log_frame.pack_forget()

    def _log_clear(self):
        self.log_text.config(state="normal"); self.log_text.delete("1.0","end"); self.log_text.config(state="disabled")

    def _log_line(self, text, color=None):
        def _ins():
            self.log_text.config(state="normal")
            tag=f"c_{color or 'def'}"; self.log_text.tag_configure(tag,foreground=color or T["FG"])
            self.log_text.insert("end",text+"\n",tag)
            self.log_text.see("end"); self.log_text.config(state="disabled")
        self.after(0,_ins)

    def _prompt_reboot(self):
        dlg=tk.Toplevel(self); dlg.title("Reboot Required")
        dlg.configure(bg=T["BG"]); dlg.geometry("420x200")
        dlg.resizable(False,False); dlg.grab_set(); dlg.transient(self)
        tk.Label(dlg,text="⚠  Kernel Updated",font=("Monospace",13,"bold"),bg=T["BG"],fg=T["KERNEL_FG"]).pack(pady=(24,6))
        tk.Label(dlg,text="A new kernel was installed.\nReboot now to apply it?",font=MONO,bg=T["BG"],fg=T["FG"],justify="center").pack(pady=(0,20))
        br=tk.Frame(dlg,bg=T["BG"]); br.pack()
        def do_reboot(): dlg.destroy(); subprocess.Popen(["sudo","reboot"])
        def dismiss(): dlg.destroy(); self.refresh_btn.enable()
        _make_btn(br,"  Reboot Now  ",do_reboot,"BTN_RED","BTN_RED_H","#ffffff").pack(side="left",padx=(0,12))
        _make_btn(br,"  Later  ",dismiss,"BTN_BG","BTN_HOVER").pack(side="left")


# ── Entry point ───────────────────────────────────────────────────────────────
def _set_window_icon(app):
    """Try to set the titlebar icon from the installed SVG, failing silently."""
    svg_path = "/usr/share/icons/hicolor/scalable/apps/arch-sysup.svg"
    # Also accept the icon next to the script for dev use
    import os
    if not os.path.exists(svg_path):
        svg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "arch-sysup.svg")
    if not os.path.exists(svg_path):
        return
    png_data = None
    # Method 1: cairosvg (pip install cairosvg)
    try:
        import cairosvg, io
        png_data = cairosvg.svg2png(url=svg_path, output_width=64, output_height=64)
    except Exception:
        pass
    # Method 2: rsvg-convert CLI tool (pacman -S librsvg)
    if png_data is None:
        try:
            result = subprocess.run(
                ["rsvg-convert", "-w", "64", "-h", "64", "-f", "png", svg_path],
                capture_output=True, timeout=5)
            if result.returncode == 0:
                png_data = result.stdout
        except Exception:
            pass
    if png_data is None:
        return
    try:
        import io
        from PIL import Image, ImageTk
        img = Image.open(io.BytesIO(png_data))
        photo = ImageTk.PhotoImage(img)
        app.iconphoto(True, photo)
        app._icon_ref = photo  # prevent garbage collection
    except Exception:
        # Fallback: use tkinter's built-in PhotoImage (PNG only, no PIL needed)
        try:
            import io, base64, tkinter as tk
            b64 = base64.b64encode(png_data).decode()
            photo = tk.PhotoImage(data=b64)
            app.iconphoto(True, photo)
            app._icon_ref = photo
        except Exception:
            pass

if __name__=="__main__":
    app=SysUpApp()
    style=ttk.Style(app); style.theme_use("clam")
    style.configure("Vertical.TScrollbar",background=T["BTN_BG"],troughcolor=T["BG_PANEL"],
                    arrowcolor=T["FG_DIM"],bordercolor=T["BORDER"])
    _set_window_icon(app)
    app.mainloop()
