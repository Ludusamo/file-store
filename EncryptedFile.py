from Crypto.Cipher import AES
from hashlib import sha256
import os, random, struct

class FileEncryptor:
    def __init__(self, password, filestore):
        self.password = password.encode('utf-8')
        self.filestore = filestore

    def encrypt(self, in_filename, out_filename=None, chunksize=64*1024):
        if not out_filename:
            out_filename = in_filename + '/content'

        key = sha256(self.password).digest()
        iv = os.urandom(16)
        encryptor = AES.new(key, AES.MODE_CBC, iv)
        filesize = os.path.getsize(in_filename)
        with open(out_filename, 'wb') as fout:
            with open(in_filename, 'rb') as fin:
                fout.write(struct.pack('<Q', filesize))
                fout.write(iv)
                while True:
                    chunk = fin.read(chunksize)
                    if len(chunk) == 0:
                        break
                    elif len(chunk) % 16 != 0:
                        chunk += b' ' * (16 - len(chunk) % 16)
                    fout.write(encryptor.encrypt(chunk))

    def decrypt(self, path, filetype='txt', chunksize=64*1024):
        with open(path, 'rb') as f:
            key = sha256(self.password).digest()
            origsize = struct.unpack('<Q', f.read(struct.calcsize('Q')))[0]
            iv = f.read(16)
            decryptor = AES.new(key, AES.MODE_CBC, iv)
            with open(path + '.' + filetype, 'wb') as out:
                while True:
                    chunk = f.read(chunksize)
                    if len(chunk) == 0:
                        break
                    out.write(decryptor.decrypt(chunk))
                out.truncate(origsize)
