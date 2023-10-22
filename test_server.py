import socket
import ssl


def main():
    with socket.socket() as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("0.0.0.0", 4444))

        s.listen(1)
        conn, addr = s.accept()
        print("Got new client:", addr)
        with conn:
            with ssl.wrap_socket(
                conn,
                server_side=True,
                keyfile="server.key",
                certfile="server.crt",
                ca_certs="client.crt",
                cert_reqs=ssl.CERT_REQUIRED,
            ) as ssl_conn:
                ssl_conn.send(b"Hello")


if __name__ == '__main__':
    main()
