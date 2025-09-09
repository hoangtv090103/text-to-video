class FileContext:
    def __init__(self, contents, filename):
        self.contents = contents
        self.filename = filename
        self.file_size = len(self.contents)
