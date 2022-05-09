import os
import time
from google.cloud import storage
from google.oauth2 import service_account

class FileLogWriter(object):

  def __init__(self, source_folder_path, sink_bucket, credentials_path):
    self.source = source_folder_path
    self.client = storage.Client()
    #self.client = storage.Client(credentials=service_account.Credentials.from_service_account_file(credentials_path))
    self.bucket = self.client.bucket(sink_bucket)
    self.registered_files = self._get_file_objects()

  def _get_file_objects(self):
    return [{"name": file, "last_modified": os.path.getmtime(f"{self.source}/{file}")} for file in os.listdir(self.source)]
  
  def detect_file_modifications(self):
    modified_files = []
    for file in self.registered_files:
      last_modified_observed = os.path.getmtime(f"{self.source}/{file.get('name')}")
      if file.get('last_modified') != last_modified_observed:
        modified_files.append({"name": file.get('name'), "last_modified": last_modified_observed})
    return modified_files

  def replace_modified_file(self, modified_file):
    files = list(filter(lambda k: k.get('name') != modified_file.get('name'), self.registered_files))
    files.append(modified_file)
    self.registered_files = files

  def write_file_to_bucket(self, destination_folder, file_name):
    blob = self.bucket.blob(f"{destination_folder}/{file_name}")
    blob.upload_from_filename(f"{self.source}/{file_name}")
    return {
        "success": True,
        "details": f"Uploaded file: {file_name}"
    }

  def _run_daemon(self, destination_folder):

    def _upload_modified_files():
      modifications = self.detect_file_modifications()
      if modifications:
        for modified_file in modifications:
          self.replace_modified_file(modified_file=modified_file)
          self.write_file_to_bucket(
              destination_folder=destination_folder,
              file_name=modified_file.get('name')
          )
    while True:
      try:
        _upload_modified_files()
      except FileNotFoundError as e:
        print(e)
        time.sleep(30)

  def run(self, destination_folder):
    for file in self.registered_files:
      try:
        self.write_file_to_bucket(
            destination_folder=destination_folder,
            file_name=file.get("name")
        )
      except Exception as e:
        print(e)
    self._run_daemon(destination_folder=destination_folder)


if __name__ == "__main__":
    l = FileLogWriter(
        source_folder_path="/path/to/logs_folder",
        sink_bucket="testbucket",
        credentials_path="/path/to/sa_credentials/sa_credentials.json"
    )
    l.run(destination_folder="destination_folder_name")
