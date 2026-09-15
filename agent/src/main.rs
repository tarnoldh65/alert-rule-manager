use std::{env, fs::File, io::{self, BufRead, BufReader, Read, Write}, net::TcpStream};

use serde::{Deserialize, Serialize};
use serde_json::Value;

#[derive(Debug, Serialize)]
struct ForwardedAlert<'a> {
    source_id: &'a str,
    payload: &'a Value,
}

fn parse_alert(line: &str) -> Result<Value, serde_json::Error> {
    serde_json::from_str(line)
}

fn forward_file(path: &str, backend: &str, source_id: &str) -> io::Result<()> {
    let file = File::open(path)?;
    let mut stream = TcpStream::connect(backend)?;
    for line in BufReader::new(file).lines() {
        let line = line?;
        if line.trim().is_empty() {
            continue;
        }
        let payload = parse_alert(&line).map_err(io::Error::other)?;
        let message = serde_json::to_vec(&ForwardedAlert { source_id, payload: &payload })?;
        stream.write_all(&message)?;
        stream.write_all(b"\n")?;
        stream.flush()?;
        let mut response = [0u8; 16];
        let _ = stream.read(&mut response);
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
    use super::parse_alert;

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
}
