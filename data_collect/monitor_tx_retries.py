import csv
import re
import subprocess
import time
from datetime import datetime

INTERFACE = "phy1-ap0"
TARGET_MAC = "5a:8f:8d:98:4f:83".lower()
OUTPUT_CSV = "tx_retries_delta.csv"
INTERVAL_SEC = 0.01  # 10 ms
HW_QUEUES_PATH = "/sys/kernel/debug/ieee80211/phy1/mt76/hw-queues"

STATION_RE = re.compile(r"^Station\s+([0-9a-fA-F:]{17})\s+\(on\s+.+\)$")
TX_RETRIES_RE = re.compile(r"^\s*tx retries:\s*(\d+)\s*$")
HW_QUEUE_RE = re.compile(r"^\s*STA\s+([0-9a-fA-F:]{17})\s+wcid\s+\d+:.*queued:(\d+)", re.IGNORECASE)


def get_station_dump() -> str:
    result = subprocess.run(
        ["iw", "dev", INTERFACE, "station", "dump"],
        capture_output=True,
        text=True,
        check=True
    )
    return result.stdout


def get_hw_queue_len(target_mac: str) -> int:
    try:
        with open(HW_QUEUES_PATH, "r") as f:
            for line in f:
                m = HW_QUEUE_RE.match(line)
                if m and m.group(1).lower() == target_mac:
                    return int(m.group(2))
    except OSError:
        pass
    return 0


def extract_tx_retries(dump_text: str, target_mac: str) -> int | None:
    current_station = None

    for line in dump_text.splitlines():
        m_station = STATION_RE.match(line)
        if m_station:
            current_station = m_station.group(1).lower()
            continue

        if current_station == target_mac:
            m_retry = TX_RETRIES_RE.match(line)
            if m_retry:
                return int(m_retry.group(1))

    return None


def main():
    last_value = None

    with open(OUTPUT_CSV, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "tx_retries_delta", "hw_queue"])

        print(f"Monitoring tx retries for station {TARGET_MAC} on {INTERFACE}")
        print(f"Writing to {OUTPUT_CSV}")
        print("Press Ctrl+C to stop.")

        try:
            while True:
                loop_start = time.time()

                try:
                    dump_text = get_station_dump()
                    current_value = extract_tx_retries(dump_text, TARGET_MAC)

                    if current_value is None:
                        print(f"[WARN] Station {TARGET_MAC} not found or tx retries missing")
                    else:
                        if last_value is None:
                            delta = 0
                        else:
                            delta = current_value - last_value
                            if delta < 0:
                                delta = 0

                        hw_queue = get_hw_queue_len(TARGET_MAC)
                        timestamp = datetime.now().isoformat(timespec="milliseconds")
                        writer.writerow([timestamp, delta, hw_queue])
                        f.flush()

                        print(f"{timestamp}, delta={delta}, current={current_value}, hw_queue={hw_queue}")
                        last_value = current_value

                except subprocess.CalledProcessError as e:
                    print(f"[ERROR] iw command failed: {e}")
                except Exception as e:
                    print(f"[ERROR] {e}")

                elapsed = time.time() - loop_start
                sleep_time = INTERVAL_SEC - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)

        except KeyboardInterrupt:
            print("\nStopped.")


if __name__ == "__main__":
    main()
