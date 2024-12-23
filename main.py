import tkinter as tk
import xml.etree.ElementTree as ET
import tarfile
from pathlib import Path
import os


class Node:
    def __init__(self, name: str, is_dir: bool = False):
        self.name = name
        self.is_dir = is_dir
        self.children = {}

    def add_child(self, child_node):
        self.children[child_node.name] = child_node

    def get_child(self, name):
        return self.children.get(name)

    def has_children(self):
        return bool(self.children)


class App:
    cur_dir: str = "/"

    def __init__(self, config_path: str) -> None:
        self._load_config(config_path)
        self._open_fs()
        self.root_node = self._build_tree()
        self._run_startup_script()
        self._gui_setup()

    def __del__(self) -> None:
        if self.fs:
            self.fs.close()

    def _open_fs(self) -> None:
        self.fs_path = Path(self.config["file_system_path"]).absolute()
        self.fs = tarfile.open(self.fs_path, 'r')

    def _build_tree(self) -> Node:
        root = Node("/", is_dir=True)
        for member in self.fs.getmembers():
            parts = member.name.strip("/").split("/")
            current_node = root
            for idx, part in enumerate(parts):
                is_dir = (idx != len(parts) - 1) or member.isdir()
                if part not in current_node.children:
                    new_node = Node(part, is_dir=is_dir)
                    current_node.add_child(new_node)
                current_node = current_node.get_child(part)
        return root
    

    def _find_node_by_path(self, parts: list) -> Node:
        current_node = self.root_node
        for part in parts:
            if not part:
                continue
            current_node = current_node.get_child(part)
            if not current_node:
                return None
        return current_node

    def _dfs_tree(self, node: Node, prefix: str = "") -> str:
        """
        Построение дерева файловой структуры с правильным форматированием.
        """
        tree_str = f"{prefix}{node.name}" + ("/\n" if node.is_dir else "\n")

        sorted_children = sorted(node.children.values(), key=lambda n: (not n.is_dir, n.name))

        for idx, child in enumerate(sorted_children):
            child_prefix = prefix + ("|  " if idx < len(sorted_children) - 1 else "   ")
            tree_str += self._dfs_tree(child, child_prefix)

        return tree_str



    def _run_startup_script(self):
        script_path = self.config.get("startup_script_path")
        if script_path and Path(script_path).exists():
            with open(script_path, "r") as script:
                for line in script:
                    self._cmd_exec(line.strip().split())

    def _ls_cmd(self, arg: list) -> str:
        path = self.cur_dir if not arg else arg[0]
        node = self._find_node_by_path(path.strip("/").split("/"))
        if node and node.has_children():
            return "\n".join(sorted(node.children.keys()))
        return ""

    def _cd_cmd(self, arg: list) -> str:
        if not arg:
            return ""
        
        target_dir = arg[0].strip("/")
        if target_dir == "..":
            if self.cur_dir != "/":
                self.cur_dir = "/".join(self.cur_dir.rstrip("/").split("/")[:-1]) or "/"
        elif target_dir == "/":
            self.cur_dir = "/"
        else:
            new_dir = f"{self.cur_dir.rstrip('/')}/{target_dir}".strip("/")
            target_node = self._find_node_by_path(new_dir.split("/"))
            if target_node and target_node.is_dir:
                self.cur_dir = f"/{new_dir}"
            else:
                return f"Directory not found: {target_dir}"
        return ""


    def _mv_cmd(self, arg: list) -> str:
        if len(arg) < 2:
            return "Usage: mv <source> <destination>"
        
        src, dest = arg[0].strip("/"), arg[1].strip("/")
        src_node = self._find_node_by_path(src.split("/"))
        dest_node = self._find_node_by_path(dest.split("/"))
        
        if not src_node:
            return f"{arg[0]} not found."
        if dest_node:
            return f"Destination {arg[1]} already exists."
        
        src_parts = src.split("/")
        src_parent = self._find_node_by_path(src_parts[:-1])
        if not src_parent:
            return f"Source parent not found: {'/'.join(src_parts[:-1])}"
        
        src_parent.children.pop(src_parts[-1])
        dest_parts = dest.split("/")
        dest_parent = self._find_node_by_path(dest_parts[:-1])
        if not dest_parent:
            return f"Destination parent not found: {'/'.join(dest_parts[:-1])}"
        
        src_node.name = dest_parts[-1]
        dest_parent.add_child(src_node)
        
        return f"{arg[0]} moved to {arg[1]}."


    def _tree_cmd(self, arg: list) -> str:
        path = self.cur_dir if not arg else arg[0]
        node = self._find_node_by_path(path.strip("/").split("/"))
        if node:
            return self._dfs_tree(node)
        return "Directory not found."

    def _exit_cmd(self, arg: list):
        self.__del__()
        exit(0)

    def _load_config(self, config_path: str) -> None:
        tree = ET.parse(config_path)
        root = tree.getroot()
        self.config = {setting.get("name"): setting.text for setting in root.findall("setting")}

    def _gui_setup(self):
        self.root = tk.Tk()
        self.text_field = tk.Text(self.root, width=50, height=25)
        self.button = tk.Button(self.root, text="Confirm", command=self._enter_handler)
        self.text_field.pack(pady=10)
        self.button.pack(pady=5)
        self.text_field.bind("<Return>", self._enter_handler)
        self.text_field.insert("1.0", f"Hello {self.config['username']}!\n{self.cur_dir} > ")

    def _enter_handler(self, event=None) -> str:
        src_line = self.text_field.get("1.0", tk.END)
        lines = src_line.strip().split("\n")
        last_line = lines[-1] 
        command = last_line.split(">")[-1].strip()
        if not command:
            return "break"
        self.text_field.insert(tk.END, f" <- Executing: {command}\n")
        result = self._cmd_exec(command.split())       
        if result:                                     
            self.text_field.insert(tk.END, f"{result}\n") 
        self.text_field.insert(tk.END, f"{self.cur_dir} > ")
        return "break"




    def _cmd_exec(self, lines: list) -> str:
        commands = {
            "ls": self._ls_cmd,
            "cd": self._cd_cmd,
            "mv": self._mv_cmd,
            "tree": self._tree_cmd,
            "exit": self._exit_cmd,
        }
        if not lines or not lines[0].strip():  # Если строка пустая, ничего не делаем
            return ""
        cmd = lines[0].strip()  # Получаем команду
        if cmd in commands:
            try:
                res = commands[cmd](lines[1:])  # Выполняем команду с аргументами
                return res if res else ""
            except Exception as e:
                return f"Error: {str(e)}"
        return f"Unknown command: {cmd}"

    
    def start(self):
        self.root.mainloop()


if __name__ == "__main__":
    config_path = Path("config.xml").absolute()
    app = App(config_path)
    app.start()
