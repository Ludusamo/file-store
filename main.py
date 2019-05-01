import sys
import EncryptedFile
import json
import os
from functools import reduce
from fuzzywuzzy import process
from getpass import getpass
import tarfile

def printUsage():
    print('Usage: {} [filestore]', sys.argv[0])

def helpMsg(*args):
    return 'To Do: Print Help message'

def search(fileEncryptor, metadata, *args):
    if len(args) < 2: return helpMsg()
    searchType = args[0]
    query = args[1]

    if searchType == 'tag':
        tags = list(
                reduce(lambda t1, t2: t1 + t2,
                map(lambda entry: entry['tags'],
                    metadata)))
        try:
            return process.extract(query, tags)
        except:
            return []
    else:
        return '{} is not a valid search type'.format(searchType)

def tag(fileEncryptor, metadata, *args):
    if len(args) < 2: return helpMsg()
    entry = int(args[0])
    tag = args[1]
    if tag not in metadata[entry]['tags']:
        metadata[entry]['tags'].append(tag)
        return 'successfully tagged {} with tag {}'.format(entry, tag)
    else:
        return 'entry {} already has tag {}'.format(entry, tag)

def untag(fileEncryptor, metadata, *args):
    if len(args) < 2: return helpMsg()
    entry = int(args[0])
    tag = args[1]
    if tag not in metadata[entry]['tags']:
        return 'entry {} does not have tag {}'.format(entry, tag)
    else:
        metadata[entry]['tags'].remove(tag)
        return 'successfully removed {} tag from {}'.format(tag, entry)

def ls(fileEncryptor, metadata, *args):
    return metadata

def quit(password, metadata, *args):
    return None

def add(fileEncryptor, metadata, *args):
    def addFile(path, name, filetype, tags):
        nextId = len(metadata)
        newEntry = \
            { 'id': nextId
            , 'name': name
            , 'filetype': filetype
            , 'tags': list(tags)
            }
        metadata.append(newEntry)
        fileEncryptor.encrypt(path, fileEncryptor.filestore + '/' + str(nextId))
        return newEntry

    if len(args) < 3: return helpMsg()
    path = args[0]
    name = args[1]
    filetype = args[2]
    tags = args[3:]
    print(path)
    if filetype == 'directory':
        with tarfile.open('dir', 'w') as dirEntry:
            dirEntry.add(path, arcname=os.path.basename(path))
        addFile('dir', name, filetype, tags)
        os.remove('dir')
    else:
        return addFile(path, name, filetype, tags)
    return None # Should never occur

dispatch = \
    { 'quit': quit
    , 'search': search
    , 'help': helpMsg
    , 'tag': tag
    , 'untag': untag
    , 'add': add
    , 'ls': ls
    }

def main():
    filestore = 'files'
    if len(sys.argv) == 2:
        filestore = sys.argv[1]
    elif len(sys.argv) > 2:
        printUsage()
        raise SystemExit

    password = getpass('Please enter password: ')
    fileEncryptor = EncryptedFile.FileEncryptor(password, filestore)
    #EncryptedFile.FileEncryptor('test', filestore).encrypt('files/ex.json', 'files/metadata')
    print(fileEncryptor)

    # Read in metadata
    metadata = None
    fileEncryptor.decrypt(filestore + '/metadata', 'json')
    with open(filestore + '/metadata.json', 'rb') as f:
        try:
            metadata = json.load(f)
        except:
            print('incorrect password', file=sys.stderr)
            return
    os.remove(filestore + '/metadata.json')
    print(metadata)

    for entry in metadata:
        pass

    while True:
        cmd = input('>> ').split(' ')
        if cmd[0] not in dispatch:
            print(helpMsg())
            continue
        # Send the rest as arguments
        res = dispatch[cmd[0]](fileEncryptor, metadata, *cmd[1:])
        if not res: break
        print(res)

    with open(filestore + '/metadata.json', 'w') as f:
        try:
            json.dump(metadata, f)
        except:
            pass

    print(password)
    fileEncryptor.encrypt(filestore + '/metadata.json', filestore + '/metadata')
    os.remove(filestore + '/metadata.json')

if __name__ == "__main__":
    main()
