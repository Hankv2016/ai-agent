# cli.py
import argparse
import sys
from client import AIClient


def main():
    parser = argparse.ArgumentParser(description="通用 AI 命令行工具")
    parser.add_argument("prompt", nargs="?", help="要发送的问题；不填则进入交互模式")
    parser.add_argument("-m", "--model", default=None, help="模型名称")
    parser.add_argument("-u", "--base-url", default=None, help="API 端点地址")
    parser.add_argument("-k", "--api-key", default=None, help="API Key")
    parser.add_argument("-i", "--interactive", action="store_true", help="强制进入交互模式")
    args = parser.parse_args()

    # 修正：Windows 控制台默认编码为 GBK，AI 回复里的 emoji / 特殊符号
    # 会导致 print 抛出 UnicodeEncodeError。强制 stdout/stderr 使用 UTF-8。
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    try:
        client = AIClient(
            api_key=args.api_key,
            base_url=args.base_url,
            model=args.model,
        )
    except ValueError as e:
        print(f"[错误] {e}", file=sys.stderr)
        sys.exit(1)

    if args.interactive or not args.prompt:
        print("进入交互模式（输入 exit 或 Ctrl+C 退出）")
        history = []  # 多轮对话上下文
        while True:
            try:
                prompt = input("\n你> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n再见！")
                break
            if not prompt:
                continue
            if prompt.lower() in ("exit", "quit"):
                break
            try:
                reply = client.chat(prompt, history=history)
                history.append({"role": "user", "content": prompt})
                history.append({"role": "assistant", "content": reply})
                print(f"\nAI> {reply}")
            except Exception as e:
                print(f"[错误] {e}", file=sys.stderr)
        return

    try:
        print(client.chat(args.prompt))
    except Exception as e:
        print(f"[错误] {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
