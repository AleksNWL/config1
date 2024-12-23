import unittest
import tarfile
import io
import xml.etree.ElementTree as ET
from pathlib import Path
from main import App

class TestApp(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.test_tar_path = Path("test_fs.tar")
        with tarfile.open(cls.test_tar_path, "w") as tar:
            file_structure = [
                ("dir1/", None),
                ("dir1/file1.txt", b"Content of file1"),
                ("dir1/file2.txt", b"Content of file2"),
                ("dir2/", None),
                ("dir2/file3.txt", b"Content of file3"),
                ("file4.txt", b"Content of file4"),
            ]
            for path, content in file_structure:
                tarinfo = tarfile.TarInfo(name=path)
                if content is not None:
                    tarinfo.size = len(content)
                    tar.addfile(tarinfo, io.BytesIO(content))
                else:
                    tar.addfile(tarinfo)
        
        cls.config_path = Path("test_config.xml")
        root = ET.Element("config")
        settings = [
            ("username", "testuser"),
            ("file_system_path", str(cls.test_tar_path)),
            ("startup_script_path", ""),
        ]
        for name, text in settings:
            setting = ET.SubElement(root, "setting", {"name": name})
            setting.text = text
        tree = ET.ElementTree(root)
        tree.write(cls.config_path)


    def setUp(self):
        # Создаем экземпляр приложения для каждого теста
        self.app = App(str(self.config_path))

    def tearDown(self):
        if hasattr(self.app, "fs") and self.app.fs:
            self.app.fs.close()  # Закрываем tarfile
        del self.app  # Удаляем экземпляр приложения


    def test_ls_root(self):
        self.assertEqual(self.app._ls_cmd([]), "dir1\ndir2\nfile4.txt")

    def test_ls_nested_dir(self):
        self.assertEqual(self.app._ls_cmd(["dir1"]), "file1.txt\nfile2.txt")

    def test_cd_to_dir(self):
        self.app._cd_cmd(["dir1"])
        self.assertEqual(self.app.cur_dir, "/")

    def test_cd_to_nonexistent_dir(self):
        result = self.app._cd_cmd(["nonexistent"])
        self.assertIn("Directory not found", result)

    def test_mv_file(self):
        result = self.app._mv_cmd(["file4.txt", "dir1/file4.txt"])
        self.assertEqual(result, "file4.txt moved to dir1/file4.txt.")
        self.assertEqual(self.app._ls_cmd(["dir1"]), "file1.txt\nfile2.txt\nfile4.txt")

    def test_mv_nonexistent_file(self):
        result = self.app._mv_cmd(["nonexistent.txt", "dir1/file5.txt"])
        self.assertIn("not found", result)

    def test_tree_root(self):
        tree_output = self.app._tree_cmd([])
        expected_output = (
            "//\n"
            "|  dir1\n"
            "|  |  file1.txt\n"
            "|     file2.txt\n"
            "|  dir2\n"
            "|     file3.txt\n"
            "   file4.txt\n"
        )
        self.assertEqual(tree_output.strip(), expected_output.strip())


    def test_tree_nested_dir(self):
        tree_output = self.app._tree_cmd(["dir1"])
        expected_output = (
            "dir1\n"
            "|  file1.txt\n"
            "   file2.txt\n"
        )
        self.assertEqual(tree_output.strip(), expected_output.strip())



    def test_exit(self):
        with self.assertRaises(SystemExit):
            self.app._exit_cmd([])

if __name__ == "__main__":
    unittest.main()