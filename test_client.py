import socket
import ssl


def main():
    with socket.socket() as s:
        s.connect(("127.0.0.1", 4444))
        ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ssl_ctx.load_cert_chain("client.crt", "client.key")
        ssl_ctx.load_verify_locations("server.crt")
        ssl_ctx.verify_mode = ssl.CERT_REQUIRED
        ssl_ctx.check_hostname = False

        ssl_conn = ssl_ctx.wrap_socket(s)
        print("Got:", ssl_conn.recv(1024))


if __name__ == "__main__":
    main()
