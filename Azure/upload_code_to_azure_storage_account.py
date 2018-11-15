#this Python script uploads the contents in the directory where you execute this script onto your Azure storage account file share. It is location where you run this script that matters, not where you saved this script.

#Prerequisite
#---Python 3.x
#---Azure SDK for Python 3.x
#---A Storage Account in Your Azure Account

from azure.storage.file import FileService
from azure.storage.file import ContentSettings
import os


omnipresence_storage_account_name = 'cloudinfraprovision'
omnipresence_storage_account_key = 'WVIc4TiKPDLxjtIWLpnk5fITbI6AFoZahvfTz4SgSjyP+fE3/qwgSgIo/UNavXPPjQDWrCfT4da6vnL209pThQ=='
omnipresence_storage_file_share = 'azure-provision' #Azure Storage Account File Share Name allows only lowercase letters, numbers and hypen.
remote_dir_path = ''


#Initialize an Azure Storage Account File Service Instance
omnipresence_storage_account = FileService(account_name=omnipresence_storage_account_name, account_key=omnipresence_storage_account_key)

#test if your storage file share exists on Azure or not, if not, create it
if (not omnipresence_storage_account.exists(omnipresence_storage_file_share)):
    omnipresence_storage_account.create_share(omnipresence_storage_file_share, quota='10')

#walk through current directory, make directorys under Azure File Share and upload local files onto your Azure storage account File Share except for hiden files and directory
for base_dir, dirs, file_names in os.walk(".", topdown=True):
    file_names = [ f for f in file_names if not f[0] == '.'] #parse out files whose name begins with a dot
    dirs[:] = [d for d in dirs if not d[0] == '.'] #parse out directorys whose name begins with a dot
    for local_file_name in file_names:
        remote_file_name = os.path.join(base_dir, local_file_name)[2:]
        local_file_name = remote_file_name
        if (omnipresence_storage_account.exists(omnipresence_storage_file_share)):
            omnipresence_storage_account.create_file_from_path(
                omnipresence_storage_file_share,
                None, # We want to create files under current remote directory, so we specify None for the directory_name
                remote_file_name,
                local_file_name,
                content_settings=ContentSettings(content_type='file'))
        print('Uploaded the file -', local_file_name, '\n')

    for directory in dirs:
        remote_dir_path = os.path.join(base_dir, directory)[2:]
        if (not omnipresence_storage_account.exists(omnipresence_storage_file_share, directory_name=remote_dir_path)):
            omnipresence_storage_account.create_directory(omnipresence_storage_file_share, remote_dir_path, metadata=None, fail_on_exist=False, timeout=None)
        print('Created the remote folder -', os.path.join(base_dir,directory)[2:])
