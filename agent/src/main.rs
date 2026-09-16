use std::{env, fs::File, io::{self, BufRead, BufReader, Read, Write}, net::TcpStream, thread, time::Duration};

use serde::Serialize;
use serde_json::Value;

#[derive(Debug, Serialize)]
struct ForwardedAlert<'a> {
    source_id: &'a str,
    payload: &'a Value,
}

fn parse_alert(line: &str) -> Result<Value, serde_json::Error> {
    serde_json::from_str(line)
}

fn connect_with_retry(backend: &str, attempts: u32, delay: Duration) -> io::Result<TcpStream> {
    let mut last_err = None;
    for attempt in 0..attempts {
        match TcpStream::connect(backend) {
            Ok(stream) => return Ok(stream),
            Err(err) => {
                eprintln!("connect to {backend} failed ({err}), attempt {}/{attempts}", attempt + 1);
                last_err = Some(err);
                if attempt + 1 < attempts {
                    thread::sleep(delay);
                }
            }
        }
    }
    Err(last_err.unwrap())
}

fn send_alert<T: Read + Write>(stream: &mut T, source_id: &str, payload: &Value) -> io::Result<()> {
    let message = serde_json::to_vec(&ForwardedAlert { source_id, payload })?;
    stream.write_all(&message)?;
    stream.write_all(b"\n")?;
    stream.flush()?;
    let mut response = [0u8; 16];
    let _ = stream.read(&mut response);
    Ok(())
}

fn forward_file(path: &str, backend: &str, source_id: &str) -> io::Result<()> {
    let file = File::open(path)?;
    let mut stream = connect_with_retry(backend, 5, Duration::from_secs(2))?;
    for line in BufReader::new(file).lines() {
        let line = line?;
        if line.trim().is_empty() {
            continue;
        }
        let payload = match parse_alert(&line) {
            Ok(payload) => payload,
            Err(err) => {
                eprintln!("skipping malformed alert line ({err}): {line}");
                continue;
            }
        };
        if let Err(err) = send_alert(&mut stream, source_id, &payload) {
            eprintln!("send to backend failed ({err}), reconnecting");
            match connect_with_retry(backend, 5, Duration::from_secs(2)) {
                Ok(reconnected) => {
                    stream = reconnected;
                    if let Err(err) = send_alert(&mut stream, source_id, &payload) {
                        eprintln!("dropping alert after reconnect failure: {err}");
                    }
                }
                Err(err) => eprintln!("dropping alert, could not reconnect to {backend}: {err}"),
            }
        }
    }
    Ok(())
}

fn main() -> io::Result<()> {
    let path = env::var("ALERT_MANAGER_ALERT_FILE").unwrap_or_else(|_| "/var/log/suricata/alert.json".into());
    let backend = env::var("ALERT_MANAGER_BACKEND").unwrap_or_else(|_| "127.0.0.1:7754".into());
    let source_id = env::var("ALERT_MANAGER_SOURCE_ID").expect("ALERT_MANAGER_SOURCE_ID is required");
    forward_file(&path, &backend, &source_id)
}

#[cfg(test)]
mod tests {
    use super::{connect_with_retry, forward_file, parse_alert, send_alert};
    use std::{
        io::Write,
        net::TcpListener,
        thread,
        time::Duration,
    };
    use tempfile::NamedTempFile;

    #[test]
    fn parses_suricata_json_line() {
        let alert = parse_alert(r#"{"timestamp":"2026-08-26T03:08:47.640421+0000","event_type":"alert","alert":{"gid":1,"signature_id":2,"rev":1,"signature":"test"}}"#).unwrap();
        assert_eq!(alert["event_type"], "alert");
        assert_eq!(alert["alert"]["signature_id"], 2);
    }

    #[test]
    fn rejects_invalid_json() {
        assert!(parse_alert("not json").is_err());
    }

    #[test]
    fn send_alert_writes_source_id_and_payload() {
        struct MockStream(Vec<u8>);
        impl std::io::Read for MockStream {
            fn read(&mut self, buf: &mut [u8]) -> std::io::Result<usize> {
                buf[..2].copy_from_slice(b"OK");
                Ok(2)
            }
        }
        impl Write for MockStream {
            fn write(&mut self, buf: &[u8]) -> std::io::Result<usize> {
                self.0.extend_from_slice(buf);
                Ok(buf.len())
            }
            fn flush(&mut self) -> std::io::Result<()> {
                Ok(())
            }
        }

        let mut mock = MockStream(Vec::new());
        let payload = parse_alert(r#"{"timestamp":"t","event_type":"alert","alert":{"gid":1,"signature_id":2,"rev":1,"signature":"s"}}"#).unwrap();
        send_alert(&mut mock, "sensor-a", &payload).unwrap();

        let sent: serde_json::Value = serde_json::from_slice(&mock.0).unwrap();
        assert_eq!(sent["source_id"], "sensor-a");
        assert_eq!(sent["payload"]["alert"]["signature_id"], 2);
    }

    #[test]
    fn connect_with_retry_gives_up_after_max_attempts() {
        let listener = TcpListener::bind("127.0.0.1:0").unwrap();
        let addr = listener.local_addr().unwrap().to_string();
        drop(listener);

        let result = connect_with_retry(&addr, 2, Duration::from_millis(10));

        assert!(result.is_err());
    }

    #[test]
    fn forward_file_skips_malformed_lines_and_forwards_valid_ones() {
        let listener = TcpListener::bind("127.0.0.1:0").unwrap();
        let addr = listener.local_addr().unwrap().to_string();

        let mut file = NamedTempFile::new().unwrap();
        writeln!(file, "not json").unwrap();
        writeln!(file, r#"{{"timestamp":"t","event_type":"alert","alert":{{"gid":1,"signature_id":2,"rev":1,"signature":"s"}}}}"#).unwrap();

        let server = thread::spawn(move || {
            let (socket, _) = listener.accept().unwrap();
            let mut writer = socket.try_clone().unwrap();
            let reader = std::io::BufReader::new(socket);
            let mut received = Vec::new();
            for line in std::io::BufRead::lines(reader) {
                let line = line.unwrap();
                received.push(line);
                writer.write_all(b"OK\n").unwrap();
            }
            received
        });

        forward_file(file.path().to_str().unwrap(), &addr, "sensor-x").unwrap();

        let received = server.join().unwrap();
        assert_eq!(received.len(), 1);
        assert!(received[0].contains("sensor-x"));
    }
}
