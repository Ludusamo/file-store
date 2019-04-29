import sys
import EncryptedFile
import json
import os
from functools import reduce
from fuzzywuzzy import process

def printUsage():
    print('Usage: {} [filestore]', sys.argv[0])

def helpMsg(*args):
    return 'To Do: Print Help message'

def search(metadata, *args):
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

def tag(metadata, *args):
    if len(args) < 2: return helpMsg()
    entry = int(args[0])
    tag = args[1]
    if tag not in metadata[entry]['tags']:
        metadata[entry]['tags'].append(tag)
        return 'successfully tagged {} with tag {}'.format(entry, tag)
    else:
        return 'entry {} already has tag {}'.format(entry, tag)

def quit(metadata, *args):
    return None

dispatch = \
    { 'quit': quit
    , 'search': search
    , 'help': helpMsg
    , 'tag': tag
    }

def main():
    #EncryptedFile.encrypt('test'.encode('utf-8'), 'files/ex.json', 'files/metadata')
    filestore = 'files'
    if len(sys.argv) == 2:
        filestore = sys.argv[1]
    elif len(sys.argv) > 2:
        printUsage()
        raise SystemExit

    password = input('Please enter password: ')

    # Read in metadata
    metadata = None
    EncryptedFile.decrypt(password.encode('utf-8'), \
            filestore + '/metadata', 'json')
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
        res = dispatch[cmd[0]](metadata, *cmd[1:]) # Send the rest as arguments
        if not res: break
        print(res)

    with open(filestore + '/metadata.json', 'w') as f:
        try:
            json.dump(metadata, f)
        except:
            pass

    print(password)
    EncryptedFile.encrypt(password.encode('utf-8'), \
            filestore + '/metadata.json', filestore + '/metadata')
    os.remove(filestore + '/metadata.json')

    #EncryptedFile.encrypt('mypass'.encode('utf-8'), 'files/test/decrypted', 'files/test/content')
    #EncryptedFile.decrypt('mypass'.encode('utf-8'), 'files/test/content')


if __name__ == "__main__":
    main()
