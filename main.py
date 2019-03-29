import EncryptedFile

def main():
    #EncryptedFile.encrypt('mypass'.encode('utf-8'), 'files/test/decrypted', 'files/test/content')
    EncryptedFile.decrypt('mypass'.encode('utf-8'), 'files/test/content')

if __name__ == "__main__":
    main()
