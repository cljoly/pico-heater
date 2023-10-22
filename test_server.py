import socket
import ssl
import struct
import time


def main():
    with socket.socket() as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("0.0.0.0", 4444))

        while True:
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
                    # ssl_conn.send(b"Hello")
                    ssl_conn.setblocking(True)
                    ssl_conn.send(struct.pack("!B", 0))
                    ssl_conn.send(struct.pack("!B", 1))
                    time.sleep(10)
                    while True:
                        print("Read: ", ssl_conn.recv(1))


if __name__ == "__main__":
    main()
