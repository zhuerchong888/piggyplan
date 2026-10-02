"""Native interaction checks for shared controls and bounded dialogs."""
from __future__ import annotations

import unittest
from types import SimpleNamespace

from piggyplan.runtime.tcl import prepare

prepare()

import tkinter as tk

from piggyplan.tokens import contrast, palette
from piggyplan.ui.dialog import Dialog
from piggyplan.ui.widgets import Card, CheckCircle, PillButton


class ControlsTests(unittest.TestCase):
    def setUp(self) -> None:
        prepare()
        self.root = tk.Tk()
        self.root.attributes("-alpha", 0)
        self.root.geometry("640x420+0+0")
        self.root.colors = palette("pink")
        self.root.font = lambda _role: ("Arial", 11)
        self.root.configure(bg=self.root.colors["surface"])
        self.callback_errors = []
        self.root.report_callback_exception = lambda *error: self.callback_errors.append(error)
        self.root.update()

    def tearDown(self) -> None:
        self.root.destroy()

    def settle(self) -> None:
        self.root.update_idletasks()
        self.root.update()

    def test_button_enter_and_space_activate_once_without_window_shortcut(self) -> None:
        calls = []
        self.root.bind("<Return>", lambda _event: calls.append("window"))
        button = PillButton(self.root, app=self.root, text="Save", command=lambda: calls.append("button"))
        button.pack()
        self.settle()
        button.focus_force()
        self.settle()
        button.event_generate("<Return>")
        button.event_generate("<space>")
        self.settle()
        self.assertEqual(calls, ["button", "button"])
        self.assertTrue(button.find_withtag("focus"), "keyboard focus must be visible")

    def test_releasing_button_outside_does_not_activate(self) -> None:
        calls = []
        button = PillButton(self.root, app=self.root, text="Save", command=lambda: calls.append(True))
        button.pack()
        self.settle()
        button.event_generate("<ButtonPress-1>", x=4, y=4)
        button.event_generate("<ButtonRelease-1>", x=button.winfo_width() + 10, y=4)
        self.assertEqual(calls, [])
        button.event_generate("<ButtonPress-1>", x=4, y=4)
        button.event_generate("<ButtonRelease-1>", x=4, y=4)
        self.assertEqual(calls, [True])

    def test_primary_uses_action_color_and_ghost_uses_parent_background(self) -> None:
        self.root.colors = {**self.root.colors, "ink": "#312B2E", "strong": "#A84162"}
        parent = tk.Frame(self.root, bg="#FAF4F6")
        primary = PillButton(parent, app=self.root, text="Save")
        ghost = PillButton(parent, app=self.root, text="Cancel", kind="ghost")
        self.assertEqual(primary._palette(False), ("#A84162", "#FFFFFF"))
        self.assertEqual(ghost._palette(False)[0], parent.cget("bg"))

    def test_checkcircle_is_keyboard_accessible_and_unchecked_has_outline(self) -> None:
        calls = []
        check = CheckCircle(self.root, app=self.root, command=lambda: calls.append(True))
        check.pack()
        self.settle()
        check.focus_force()
        self.settle()
        check.event_generate("<Return>")
        check.event_generate("<space>")
        self.assertEqual(calls, [True, True])
        self.assertTrue(str(check.cget("takefocus")) in {"1", "true"})
        self.assertTrue(check.find_withtag("focus"))
        outlines = [check.itemcget(item, "outline") for item in check.find_withtag("indicator")]
        self.assertTrue(outlines)
        self.assertGreaterEqual(contrast(outlines[0], check.cget("bg")), 3)

    def test_card_hover_recolors_matching_descendants_and_preserves_tinted_regions(self) -> None:
        card = Card(self.root, app=self.root, hoverable=True)
        card.pack(fill="x")
        previous = card.body.cget("bg")
        row = tk.Frame(card.body, bg=previous)
        row.pack()
        label = tk.Label(row, text="Task", bg=previous)
        label.pack()
        tinted = tk.Frame(row, bg=self.root.colors["soft"])
        tinted.pack()
        card.hover(True)
        self.assertEqual(row.cget("bg"), card.body.cget("bg"))
        self.assertEqual(label.cget("bg"), card.body.cget("bg"))
        self.assertEqual(tinted.cget("bg"), self.root.colors["soft"])
        card.hover(False)
        self.assertEqual(label.cget("bg"), previous)

    def test_destroyed_card_cancels_widget_callbacks(self) -> None:
        card = Card(self.root, app=self.root, hoverable=True)
        card.pack(fill="x")
        self.settle()
        card._follow_canvas(SimpleNamespace(width=500, height=80))
        card.body.event_generate("<Leave>")
        owned_commands = tuple(card._tclCommands or ())
        card.destroy()
        pending_scripts = [str(self.root.tk.call("after", "info", callback))
                           for callback in self.root.tk.call("after", "info")]
        self.assertFalse(any(name in script for name in owned_commands for script in pending_scripts))
        self.settle()

    def test_overflow_dialog_caps_height_and_keeps_footer_visible(self) -> None:
        dialog = Dialog(self.root, "Long form", "420x260")
        dialog.attributes("-alpha", 0)
        dialog.winfo_screenheight = lambda: 500
        tk.Frame(dialog.content, height=1200, bg=self.root.colors["surface"]).pack(fill="x")
        save = PillButton(dialog.footer_actions, app=self.root, text="Save")
        save.pack(side="right")
        self.settle()
        self.assertLessEqual(dialog.winfo_height(), 400)
        self.assertGreaterEqual(save.winfo_rooty(), dialog.winfo_rooty())
        self.assertLessEqual(save.winfo_rooty() + save.winfo_height(), dialog.winfo_rooty() + dialog.winfo_height())
        self.assertTrue(hasattr(dialog, "content_canvas"))
        first = dialog.content_canvas.yview()
        dialog.scroll(SimpleNamespace(delta=-120, num=None, widget=dialog.content))
        self.settle()
        self.assertGreater(dialog.content_canvas.yview()[0], first[0])
        dialog.destroy()
        self.settle()
        self.assertEqual(self.callback_errors, [])

    def test_focusing_offscreen_dialog_field_reveals_it(self) -> None:
        dialog = Dialog(self.root, "Long form", "420x260")
        dialog.attributes("-alpha", 0)
        dialog.winfo_screenheight = lambda: 500
        tk.Frame(dialog.content, height=800, bg=self.root.colors["surface"]).pack(fill="x")
        entry = tk.Entry(dialog.content)
        entry.pack(fill="x")
        tk.Button(dialog.footer_actions, text="Save").pack(side="right")
        self.settle()
        entry.focus_force()
        self.settle()
        canvas = dialog.content_canvas
        self.assertGreater(canvas.yview()[0], 0)
        self.assertGreaterEqual(entry.winfo_rooty(), canvas.winfo_rooty())
        self.assertLessEqual(entry.winfo_rooty() + entry.winfo_height(), canvas.winfo_rooty() + canvas.winfo_height())


if __name__ == "__main__":
    unittest.main()
