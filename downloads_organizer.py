from pathlib import Path
from datetime import datetime,date
import time
from time import sleep

def log_file_write(message:str):
    with open("download_organizer_report.txt" , "a") as file:
        file.write(f"{message}\n")

class DownloadFile:
    def __init__(self,path: Path,created_at: datetime,size_bytes: int):
        self.path = path # Path object has useful info about a specified file
        self.created_at = created_at # datetime object, has useful datime methods to use later (Year, month, day,...)
        self.size_bytes = size_bytes # size of the specified file in bytes

    @property
    def name(self)->str:
        """return specified file's name"""
        return self.path.name

    @property
    def extension(self)->str:
        """return the type (.extension) of the specified file"""
        return self.path.suffix.lower()

    @property
    def created_date(self)->"date":
        """return the file's date of creation"""
        return self.created_at.date()

    @classmethod
    def from_path(cls,path: Path) -> "DownloadFile":
        """receives a Path('file.something') object that has specific info about a file, and then constructs a DownloadFile obj with these info"""

        '''Η getattr() δεν ειναι μεθοδος της Pathlib. αλλά στην ουσία λέει από το object file_info
         παρε το ονομα του attribute st_birthtime (file_info.st_birthtime).
          Αν δεν υπάρχει πάρε το default που βάλαμε -> file_info.st_ctime.
          Αυτο το κάναμε γιατι προτιμάται η st_birthtime εναντι της st_ctime στα  Windows'''

        file_info = path.stat()
        file_date_creation = getattr(file_info, "st_birthtime", file_info.st_ctime) # Path() method, returns the file's day of creation
        format_date = datetime.fromtimestamp(file_date_creation) #formating the file's date of creation so we can create a datetime object
        return cls (path,format_date,path.stat().st_size)

    def is_older_than(self,day : date):
        """Check if the file is older than the given date"""
        return self.created_date < day
    def __str__(self)->str:
        return f"File: {self.name} |path: {self.path.absolute()} | created at: {self.created_date} | size (in bytes): {self.size_bytes}"

class FileClassifier:
    def __init__(self,categories: dict[str, list[str]]):
        self.categories = categories

    def classify(self,file: DownloadFile) -> str:
        """receives a DownloadFile obj ant returns the category that the file belongs to"""
        for key in self.categories:
            for extension in self.categories[key]:
                if file.extension == extension.lower():
                    return key
        return "Other"

class DownloadScanner:
    def __init__(self, downloads_folder: Path, ignored_suffixes: set[str], ignored_names: set[str]):
        self.downloads_folder = downloads_folder
        self.ignored_suffixes = {suffix.casefold() for suffix in ignored_suffixes}
        self.ignored_names = {name.casefold() for name in ignored_names}

    def scan(self) -> list[DownloadFile]:
        download_file_list = []
        for file in self.downloads_folder.iterdir():
            if file.is_symlink() or not file.is_file():
                continue
            if not self.should_ignore(file):
                #if file isn't part of the ignored types, proceed
                download_file_list.append(DownloadFile.from_path(file))
        return download_file_list


    def should_ignore(self,path: Path) -> bool:
        temporary_path = path.with_name(path.name + ".part") #.part is a temporary, incomplete file created by web browsers.
        if temporary_path.exists():
            return True
        if path.name.casefold() in self.ignored_names or path.suffix.casefold() in self.ignored_suffixes:
            return True
        else:
            return False

class FileMover:
    def __init__(self,downloads_folder: Path):
        #λαμβανει το αντικείμενο Path() το οποιο αφορα το Downloads folder
        self.downloads_folder = downloads_folder

    def build_destination(self, file: DownloadFile, category: str) -> "Path":
        """Υπολογίζει την πλήρη διαδρομή προορισμού του αρχείου."""
        return self.downloads_folder / category / file.name

    def get_unique_destination(self, destination: Path) -> Path:
        """Επιστρέφει διαθέσιμο Path χωρίς να δημιουργεί ή να μετακινεί αρχεία."""
        candidate = destination
        i = 1

        while candidate.exists():
            candidate = destination.with_name(
                f"{destination.stem} ({i}){destination.suffix}"
            )
            i += 1

        return candidate
    def move(self,file:DownloadFile, category:str) -> "Path":
        destination = self.build_destination(file,category)
        unique_destination = self.get_unique_destination(destination)
        unique_destination.parent.mkdir(exist_ok=True)

        new_path = file.path.rename(unique_destination)
        file.path = new_path
        print("File Moved")
        return new_path

class DownloadOrganizer:
    def __init__(self,scanner: DownloadScanner, classifier: FileClassifier, mover: FileMover):
        self.scanner = scanner
        self.classifier = classifier
        self.mover = mover

    def organize_once(self,today: date | None = None, dry_run: bool = True) -> dict:
        if today == None:
            today = date.today()
        files_scanned = self.scanner.scan()
        total_files = sum(1 for item in self.scanner.downloads_folder.iterdir() if item.is_file())
        files_moved = 0
        planned = 0
        failed = 0


        #Work with files that are not created today!
        category = ""
        for file in files_scanned:
            if  file.is_older_than(today):
                category =self.classifier.classify(file)
                if not dry_run:
                    try:
                        self.mover.move(file,category)
                        files_moved +=1
                    except OSError as error:
                        failed +=1
                        print(f"Could not move {file.name}: {error}")
                else:
                    planned +=1
        skipped = total_files - files_moved - planned - failed
        return {"scanned":total_files,"moved":files_moved,"planned":planned,"skipped":skipped,"failed":failed}

class OrganizerRunner:
    def __init__(self,organizer: DownloadOrganizer, interval_seconds: int = 3600, dry_run: bool = True):
        self.organizer = organizer
        self.interval_seconds = interval_seconds
        self.dry_run = dry_run
        self.running = False

    @property
    def interval_seconds(self):
        return self._interval_seconds

    @interval_seconds.setter
    def interval_seconds(self,new_value):
        if type(new_value) is not int or new_value <= 0 :
            raise ValueError ("Interval must be a positive integer number!")
        self._interval_seconds = new_value

    def run_forever(self) -> None:
        self.running = True
        day_today = date.today()
        log_file_write(f"------------------------- Data for {date.today()} -------------------------")
        try:
            start_session = time.monotonic()
            report = self.organizer.organize_once(dry_run=self.dry_run)
            print(report)
            log_file_write(f"\t{report}")
            while self.running:
                if time.monotonic() - start_session >= self.interval_seconds:
                    report = self.organizer.organize_once(dry_run=self.dry_run)
                    start_session = time.monotonic()
                    print(report)
                    if date.today() is not day_today:
                        # make the report only appear once a day!
                        day_today = date.today()
                        log_file_write(f"------------------------- Data for {date.today()} -------------------------")
                sleep(1)
            print("Script terminated")
        except KeyboardInterrupt:
            self.stop()
            print("Script terminated ")
    def stop(self):
        self.running =False

# Main
categories = {
    "Audio": [".mp3", ".wav", ".flac", ".m4a"],
    "Images": [".jpg", ".jpeg", ".png", ".gif", ".webp"],
    "Videos": [".mp4", ".mkv", ".webm", ".avi", ".mov"],
    "Documents": [".pdf", ".docx", ".txt", ".xlsx", ".csv"],
    "Archives": [".zip", ".rar", ".7z", ".tar", ".gz"]
}

file_classifier = FileClassifier(categories) #---------------------1

ignored_suff = {".crdownload", ".part", ".tmp", ".lnk"}
ignored_names = {"desktop.ini", "Thumbs.db"}

test_path = Path.home() / 'Downloads' #Path().cwd() / "downloads_test"
scanner = DownloadScanner(test_path,ignored_suff,ignored_names) #-------------------2
files_found = scanner.scan()

#downloads_path = Path.home() / 'Downloads'
file_move = FileMover(test_path) #------------------------------------ 3

organizer = DownloadOrganizer(scanner,file_classifier,file_move)
runner = OrganizerRunner(organizer,interval_seconds=300,dry_run=False)
runner.run_forever()
