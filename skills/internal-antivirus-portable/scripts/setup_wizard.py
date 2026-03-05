#!/usr/bin/env python3
"""Interactive setup wizard for portable internal-antivirus."""

from __future__ import annotations

import argparse
from pathlib import Path
import yaml


def ask(prompt: str, default: str = "") -> str:
    tail = f" [{default}]" if default else ""
    v = input(f"{prompt}{tail}: ").strip()
    return v if v else default


def main() -> int:
    base = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Configure portable internal-antivirus")
    parser.add_argument("--policy", default=str(base / "policy.yaml"))
    parser.add_argument("--non-interactive", action="store_true")
    parser.add_argument("--channel", default="")
    parser.add_argument("--chat-id", default="")
    parser.add_argument("--thread-id", default="")
    parser.add_argument("--topic", default="")
    parser.add_argument("--owner", default="")
    args = parser.parse_args()

    p = Path(args.policy).expanduser().resolve()
    policy = yaml.safe_load(p.read_text(encoding="utf-8"))

    if args.non_interactive:
        channel = args.channel or "local"
        chat_id = args.chat_id
        thread_id = args.thread_id
        topic = args.topic
        owner = args.owner or policy.get("owner", "local-owner")
    else:
        print("Internal Antivirus setup wizard")
        print("Choose delivery mode:")
        print("1) local only (default)")
        print("2) telegram delivery lock")
        mode = ask("Select mode 1/2", "1")

        owner = ask("Owner label", str(policy.get("owner", "local-owner")))

        if mode == "2":
            channel = "telegram"
            chat_id = ask("Telegram chat_id (required)")
            thread_id = ask("Telegram thread/topic id", "")
            topic = ask("Topic label", "")
        else:
            channel = "local"
            chat_id = ""
            thread_id = ""
            topic = ""

    policy["owner"] = owner
    lock = policy.setdefault("report_delivery_lock", {})
    lock["enabled"] = channel != "local"
    lock["channel"] = channel
    lock["chat_id"] = str(chat_id)
    lock["thread_id"] = str(thread_id)
    lock["topic"] = str(topic)

    p.write_text(yaml.safe_dump(policy, sort_keys=False, allow_unicode=True), encoding="utf-8")
    print(f"✅ Updated policy: {p}")
    if lock["enabled"]:
        print(f"Delivery lock set: {channel} chat_id={lock['chat_id']} thread_id={lock['thread_id']} topic={lock['topic']}")
    else:
        print("Delivery lock disabled (local mode).")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
