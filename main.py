import sys
import EncryptedFile
import json
import os
from functools import reduce
from fuzzywuzzy import process
from getpass import getpass
from termcolor import colored
import tarfile
import argparse
from itertools import islice
from random import sample
from multiprocessing.dummy import Pool as ThreadPool
from multiprocessing import cpu_count

def printUsage():
    print('Usage: {} [filestore]', sys.argv[0])

def entryToString(entry):
    def longStr(item, l):
        s = str(item)
        if len(s) > l:
            if type(item) == list:
                return s[:l-4] + '...]'
            else:
                return s[:l-3] + '...'
        return s

    return colored('{:4}'.format(entry['id']), 'red') + '|' + \
        colored('{:40}'.format(longStr(entry['name'], 40)), 'white') + '|' + \
        colored('{:4}'.format(entry['filetype']), 'yellow') + '|' + \
        colored('{}'.format(longStr(entry['tags'], 52)), 'blue')

def filterFiles(metadata, cmdArgs):
    def isSubset(l1, l2): return all(map(lambda i: i in l2, l1))
    def hasNone(l1, l2): return not any(map(lambda i: i in l2, l1))
    try:
        subset = metadata
        if cmdArgs.name != '':
            matches = process.extract(cmdArgs.name, \
                map(lambda f: f['name'], metadata))
            subset = map(lambda match: \
                next(e for e in metadata \
                    if e['name'] == match[0]),
                filter(lambda m: m[1] > 80, matches)) # Take matches >80 percent

        # remove if not in id list if id list is not empty
        filteredEntries = \
            filter(lambda f: not cmdArgs.id or f['id'] in cmdArgs.id,
                # include all of these
                filter(lambda f: isSubset(cmdArgs.tags, f['tags']),
                # Don't include any of these
                filter(lambda f: hasNone(cmdArgs.nottags, f['tags']),
                    subset)))
        if cmdArgs.num > 0:
            if cmdArgs.rand:
                return sample(
                    [e for e in filteredEntries],
                    cmdArgs.num)
            return [next(filteredEntries) for i in range(cmdArgs.num)]
        else: return filteredEntries
    except: return []

def search(fileEncryptor, metadata, cmdArgs, *args):
    if len(args) < 1: return helpMsg()
    searchType = args[0]

    if searchType == 'tag':
        tags = reduce(lambda t1, t2: t1 + t2,
                map(lambda entry: entry['tags'],
                    metadata))
        if len(args) < 2: return colored(', '.join(set(tags)), 'blue')
        query = args[1]
        try:
            return colored(', '.join(map(lambda t: t[0] ,
                filter(lambda t: t[1] > 80,
                    process.extract(query, set(tags))))), 'blue')
        except:
            return []
    elif searchType == 'file':
        return '\n'.join(map(lambda f: entryToString(f), \
                filterFiles(metadata, cmdArgs)))
    else:
        return '{} is not a valid search type'.format(searchType)

def tag(fileEncryptor, metadata, cmdArgs, *args):
    if len(args) < 1: return 'insufficient arguments: expected file id'
    entry = int(args[0])
    msgs = []
    for tag in cmdArgs.tags:
        if tag not in metadata[entry]['tags']:
            metadata[entry]['tags'].append(tag)
            msgs.append('successfully tagged {} with tag {}'
                .format(colored(entry, 'red'), colored(tag, 'blue')))
        else:
            msgs.append('entry {} already has tag {}'
                .format(colored(entry, 'red'), colored(tag, 'blue')))
    return '\n'.join(msgs)

def untag(fileEncryptor, metadata, cmdArgs, *args):
    if len(args) < 1: return 'insufficient arguments: expected file id'
    entry = int(args[0])
    msgs = []
    for tag in cmdArgs.tags:
        if tag not in metadata[entry]['tags']:
            msgs.append('entry {} does not have tag {}'
                .format(colored(entry, 'red'), colored(tag, 'blue')))
        else:
            metadata[entry]['tags'].remove(tag)
            msgs.append('successfully removed {} tag from {}'
                .format(colored(tag, 'blue'), colored(entry, 'red')))
    return '\n'.join(msgs)

def add(fileEncryptor, metadata, cmdArgs, *args):
    def addFile(path, name, filetype, tags):
        nextId = metadata[-1]['id'] + 1 if len(metadata) > 0 else 0
        newEntry = \
            { 'id': nextId
            , 'name': name
            , 'filetype': filetype
            , 'tags': list(tags)
            }
        metadata.append(newEntry)
        fileEncryptor.encrypt(path, fileEncryptor.filestore + '/' + str(nextId))
        return newEntry

    if len(args) < 1: return helpMsg()
    path = args[0]
    filename = path.split('/')[-1]
    name = cmdArgs.name if cmdArgs.name else filename.split('.')[0]
    filetype = cmdArgs.type if cmdArgs.type else filename.split('.')[1]
    tags = list(set(cmdArgs.tags))
    if filetype == 'dir':
        with tarfile.open('dir.tar.gz', 'w:gz') as dirEntry:
            dirEntry.add(path, arcname=os.path.basename(path))
        entry = addFile('dir.tar.gz', name, filetype, tags)
        os.remove('dir.tar.gz')
        return entryToString(entry)
    return entryToString(addFile(path, name, filetype, tags))

def get(fileEncryptor, metadata, cmdArgs, *args):
    dirPath = fileEncryptor.filestore + '/unencrypted'
    if cmdArgs.dest: dirPath = cmdArgs.dest
    def decryptFile(f):
        fileId = f['id']
        fileData = metadata[fileId]
        if fileData['filetype'] == 'dir':
            folderPath = dirPath + '/' + fileData['name']
            os.makedirs(folderPath)
            fileEncryptor.decrypt(fileEncryptor.filestore + '/' + str(fileId), \
                    dirPath + '/' + fileData['name'], 'tar.gz')
            tarpath = dirPath + '/' + fileData['name'] + '.tar.gz'
            tar = tarfile.open(tarpath, 'r:gz')
            tar.extractall(path=folderPath)
            tar.close()
            os.remove(tarpath)
        else:
            fileEncryptor.decrypt(fileEncryptor.filestore + '/' + str(fileId), \
                    dirPath + '/' + fileData['name'], fileData['filetype'])
        print('Decrypted:', colored(f['name'], 'white'))
    if not os.path.exists(dirPath):
        os.makedirs(dirPath)
    pool = ThreadPool(cpu_count())
    files = filterFiles(metadata, cmdArgs)
    pool.map(decryptFile, files)
    pool.close()
    pool.join()
    return 'Done!'

def remove(fileEncryptor, metadata, cmdArgs, *args):
    if len(args) < 1: return 'insufficient arguments: expected file id'
    fileId = int(args[0])
    if fileId >= len(metadata) or fileId < 0:
        return 'id {} does not exist'.format(fileId)
    os.remove(fileEncryptor.filestore + '/' + str(fileId))
    for i in range(fileId + 1, len(metadata)):
        metadata[i]['id'] = i - 1
        metadata[i - 1] = metadata[i]
        os.rename(fileEncryptor.filestore + '/' + str(i), \
                fileEncryptor.filestore + '/' + str(i - 1))
    metadata.pop()
    return 'successfully removed {}'.format(fileId)

def filetype(fileEncryptor, metadata, cmdArgs, *args):
    if len(args) < 1: return 'insufficient arguments: expected file id'
    fileId = int(args[0])
    filetype = cmdArgs.type
    metadata[fileId]['filetype'] = filetype
    return 'successfully set file {} filetype to {}'.format(fileId, filetype)

def changepass(fileEncryptor, metadata, cmdArgs, *args):
    if len(args) < 1: return 'insufficient arguments: expected new password'
    oldEncryptor = EncryptedFile.FileEncryptor( \
            fileEncryptor.password.decode(), \
            fileEncryptor.filestore)
    fileEncryptor.password = args[0].encode('utf-8')
    def rehash(e):
        print('Rehashing:', colored(e['name'], 'white'))
        path = fileEncryptor.filestore + '/' + str(e['id'])
        oldEncryptor.decrypt(path, path, 'temp')
        fileEncryptor.encrypt(path + '.temp', path)
        os.remove(path + '.temp')
    pool = ThreadPool(cpu_count())
    pool.map(rehash, metadata)
    pool.close()
    pool.join()
    return 'Done!'

dispatch = \
    { 'search': search
    , 'tag': tag
    , 'untag': untag
    , 'add': add
    , 'get': get
    , 'remove': remove
    , 'filetype': filetype
    , 'changepass': changepass
    }

def main(args):
    filestore = args.source

    password = getpass('Please enter password: ')
    fileEncryptor = EncryptedFile.FileEncryptor(password, filestore)
    #EncryptedFile.FileEncryptor('test', filestore).encrypt('files/ex.json', 'files/metadata')

    # Read in metadata
    metadata = None
    if os.path.exists(filestore + '/metadata'):
        fileEncryptor.decrypt(filestore + '/metadata', \
                filestore + '/metadata', 'json')
        with open(filestore + '/metadata.json', 'rb') as f:
            try:
                metadata = json.load(f)
            except:
                print('incorrect password', file=sys.stderr)
                return
        os.remove(filestore + '/metadata.json')

    if not metadata:
        metadata = []
        print('repository initialized')

    print(dispatch[args.cmd](fileEncryptor, metadata, args, *args.args))

    with open(filestore + '/metadata.json', 'w') as f:
        try:
            json.dump(metadata, f)
        except:
            pass

    fileEncryptor.encrypt(filestore + '/metadata.json', filestore + '/metadata')
    os.remove(filestore + '/metadata.json')

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    def validCmd(cmd):
        if cmd not in dispatch:
            msg = '%s is not a valid command' % cmd
            raise argparse.ArgumentTypeError(msg)
        return cmd
    parser.add_argument('cmd', type=validCmd,
        help='command to be dispatched')
    parser.add_argument('args', nargs='*',
        help='arguments to specific commands')
    parser.add_argument('-s', '--source', required=True,
        help='path to source folder')
    parser.add_argument('-d', '--dest',
        help='path to destination folder of unencrypted files')
    parser.add_argument('-i', '--id', type=int, nargs='+', default=[],
        help='ids of desired elements')
    parser.add_argument('-t', '--tags', nargs='+', default=[],
        help='associated tags with request')
    parser.add_argument('-nt', '--nottags', nargs='+', default=[],
        help='exclusion list for tags')
    parser.add_argument('-n', '--name', default='',
        help='name of file')
    parser.add_argument('-ft', '--type',
        help='associated filetype')
    parser.add_argument('-nu', '--num', type=int, default=-1,
        help='number of results desired')
    parser.add_argument('-r', '--rand', action='store_true',
        help='enable randomization of output')
    args = parser.parse_args()
    main(args)
