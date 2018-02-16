import requests

def main():
    host = 'localhost'
    port = '8000'
    r = requests.get("http://{}:{}/getSqlData".format(host,port))
    print (r.content)


if __name__ == '__main__':
    main()