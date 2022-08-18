import json
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import sys
import hashlib
from pathlib import Path
from shutil import copyfile

def ComputeMD5(inPath:Path) -> str:
    if not inPath.exists():
        return ""
    bytes = inPath.read_bytes()
    hash = hashlib.md5(bytes)
    return hash.hexdigest()

class SettingManager():
    cSetting = Path('./setting.json')

    def __init__(self) -> None:
        if self.cSetting.exists():
            self.mGameInstallPath = json.loads(self.cSetting.read_text(encoding="utf-8"))["GameInstallPath"]
        else:
            dialog = QFileDialog()
            dialog.setWindowTitle("Where is game?")
            dialog.setFileMode(QFileDialog.FileMode.DirectoryOnly)
            if dialog.exec_() == QDialog.DialogCode.Accepted:
                self.mGameInstallPath = dialog.selectedFiles()[0]
                self.cSetting.write_text(json.dumps({"GameInstallPath" : self.mGameInstallPath}, indent=4))

    @property
    def GameInstallPath(self) -> Path:
        return Path(self.mGameInstallPath)

class FileController():
    def __init__(self, inSource:Path, inDest:Path) -> None:
        self.mSource = inSource
        self.mDest = inDest
        self.mInstalled = False

    def Copy(self):
        self.mDest.parent.mkdir(exist_ok=True, parents=True)
        print("Copy", str(self.Source), "=>", str(self.Dest))
        copyfile(str(self.Source), str(self.Dest))

    def Delete(self):
        print("Delete", str(self.Dest))
        self.Dest.unlink(missing_ok=True)

    def Move(self):
        pass

    @property
    def Source(self) -> Path:
        return self.mSource

    @property
    def Dest(self) -> Path:
        return self.mDest

    @property
    def IsMatch(self) -> bool:
        return ComputeMD5(self.mDest) == ComputeMD5(self.mSource)

class ModContoller():
    def __init__(self, inPath:Path, inGameInstallPath:Path) -> None:
        self.mPath = inPath
        self.mName = inPath.name
        self.mGameInstallPath = inGameInstallPath
        self.mFiles = []
        self.mInstalled = False

    def Install(self):
        for file in self.mFiles:
            file.Copy()
        self.__check_installed__()

    def Uninstall(self):
        for file in self.mFiles:
            file.Delete()
        self.__check_installed__()
    
    def __check_installed__(self):
        for file in self.mFiles:
            if not file.IsMatch:
                self.mInstalled = False
                return
        self.mInstalled = True

    @property
    def Installed(self) -> bool:
        return self.mInstalled
    
    @property
    def ModName(self) -> str:
        return self.mName

class ReFrameworkApplication(ModContoller):
    def __init__(self, inPath: Path, inGameInstallPath:Path) -> None:
        super().__init__(inPath, inGameInstallPath)
        source = inPath / "dinput8.dll"
        dest = self.mGameInstallPath / "dinput8.dll"
        self.mFiles.append(FileController(source, dest))
        self.__check_installed__()

class ReFrameworkModController(ModContoller):
    def __init__(self, inPath: Path, inGameInstallPath:Path) -> None:
        super().__init__(inPath, inGameInstallPath)
        reframework = inPath / "reframework"
        for f in reframework.glob("**/*"):
            if f.is_dir():
                continue
            relative = ""
            relative = f.relative_to(inPath)
            self.mFiles.append(FileController(f, self.mGameInstallPath / relative))
        self.__check_installed__()

class FirstNativeModController(ModContoller):
    def __init__(self, inPath: Path, inGameInstallPath:Path) -> None:
        super().__init__(inPath, inGameInstallPath)
        natives = inPath / "natives"
        for f in natives.glob("**/*"):
            if f.is_dir():
                continue
            relative = ""
            relative = f.relative_to(inPath)
            self.mFiles.append(FileController(f, self.mGameInstallPath / relative))
        self.__check_installed__()

class FactoryModController():
    
    @staticmethod
    def Create(inPath:Path, inGameInstallPath:Path):
        name = inPath.name
        if "REFramework" == name:
            return ReFrameworkApplication(inPath, inGameInstallPath)
        else:
            for mod in inPath.glob("*"):
                if "natives" == mod.name: 
                    return FirstNativeModController(inPath, inGameInstallPath)
                if "reframework" == mod.name:
                    return ReFrameworkModController(inPath, inGameInstallPath)

class ModManagerWindow(QWidget):
    cMods = Path("./Mods")

    def __init__(self, inSetting:SettingManager):
        QWidget.__init__(self)
        self.cMods.mkdir(parents=True, exist_ok=True)
        self.mGameInstallPath = inSetting.GameInstallPath
        self.setFixedWidth(500)
        self.setWindowTitle("MHRise ModManager")
        layout = QGridLayout()
        self.setLayout(layout)
        self.mModList = QListWidget()
        
        for mod in self.RefreshModList():
            self.mModList.insertItem(0, mod)
        layout.addWidget(self.mModList, 0, 0)

        button = QPushButton("Go!")
        button.clicked.connect(self.Go)
        layout.addWidget(button, 1, 0)

    def RefreshModList(self) -> list[QListWidgetItem]:
        for mod in self.cMods.glob("*"):
            if  "HunterPie" in mod.name:
                continue
            user_data = FactoryModController.Create(mod, self.mGameInstallPath)
            item = QListWidgetItem(mod.name)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if user_data.Installed else Qt.CheckState.Unchecked)
            item.setData(Qt.ItemDataRole.UserRole, user_data)
            yield item

    def Go(self):
        for c in range(self.mModList.count()):
            item = self.mModList.item(c)
            controller = item.data(Qt.ItemDataRole.UserRole)
            if item.checkState() == Qt.CheckState.Checked:
                if not controller.Installed:
                    controller.Install()
            elif item.checkState() == Qt.CheckState.Unchecked:
                if controller.Installed:
                    controller.Uninstall()
            item.setCheckState(Qt.CheckState.Checked if controller.Installed else Qt.CheckState.Unchecked)

if __name__ == "__main__":
    app = QApplication(sys.argv)

    main = ModManagerWindow(SettingManager())
    main.show()
    sys.exit(app.exec_())