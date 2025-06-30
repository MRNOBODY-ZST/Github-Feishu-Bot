import os
import json
import hmac
import hashlib
from datetime import datetime, timezone, timedelta
from flask import Flask, request, jsonify
import lark_oapi as lark
from lark_oapi.api.im.v1 import *
from config import FEISHU_CHAT_ID, GITHUB_WEBHOOK_SECRET, LARK_APP_ID, LARK_APP_SECRET

app = Flask(__name__)

# 创建飞书客户端
client = lark.Client.builder().app_id(LARK_APP_ID).app_secret(LARK_APP_SECRET).build()


def verify_github_signature(payload_body, signature_header):
    """验证GitHub Webhook签名"""
    if not GITHUB_WEBHOOK_SECRET:
        return True  # 如果没有设置密钥，跳过验证

    signature = hmac.new(
        GITHUB_WEBHOOK_SECRET.encode("utf-8"), payload_body, hashlib.sha256
    ).hexdigest()

    expected_signature = f"sha256={signature}"
    return hmac.compare_digest(expected_signature, signature_header)


def send_feishu_message(message_content):
    """发送消息到飞书群组"""
    try:
        request = (
            CreateMessageRequest.builder()
            .receive_id_type("chat_id")
            .request_body(
                CreateMessageRequestBody.builder()
                .receive_id(FEISHU_CHAT_ID)
                .msg_type("interactive")
                .content(message_content)
                .build()
            )
            .build()
        )

        response = client.im.v1.message.create(request)
        if not response.success():
            print(f"发送飞书消息失败: {response.code}, {response.msg}")
            return False
        return True
    except Exception as e:
        print(f"发送飞书消息异常: {str(e)}")
        return False


def create_push_card(payload):
    """创建Push事件卡片"""
    repository = payload["repository"]
    pusher = payload["pusher"]
    commits = payload["commits"]

    # 构建提交列表
    commit_elements = []
    for commit in commits[:5]:  # 最多显示5个提交
        commit_elements.append(
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**[{commit['id'][:7]}]({commit['url']})** {commit['message']}\n👤 {commit['author']['name']}",
                },
            }
        )

    if len(commits) > 5:
        commit_elements.append(
            {
                "tag": "div",
                "text": {
                    "tag": "plain_text",
                    "content": f"... 还有 {len(commits) - 5} 个提交",
                },
            }
        )

    card_content = {
        "type": "template",
        "data": {"template_id": "", "template_variable": {}},
    }

    # 如果没有模板ID，使用自定义卡片
    card_content = {
        "config": {"wide_screen_mode": True},
        "elements": [
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"🚀 **代码推送通知**\n\n**仓库:** [{repository['name']}]({repository['html_url']})\n**分支:** {payload['ref'].replace('refs/heads/', '')}\n**推送者:** {pusher['name']}\n**提交数量:** {len(commits)}",
                },
            },
            {"tag": "hr"},
            {"tag": "div", "text": {"tag": "lark_md", "content": "**📝 提交详情:**"}},
        ]
        + commit_elements
        + [
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "查看仓库"},
                        "type": "primary",
                        "url": repository["html_url"],
                    }
                ],
            }
        ],
    }

    return json.dumps(card_content)


def create_pr_card(payload, action):
    """创建Pull Request事件卡片"""
    pr = payload["pull_request"]
    repository = payload["repository"]

    action_text = {
        "opened": "🆕 新建",
        "closed": "✅ 关闭" if pr["merged"] else "❌ 关闭",
        "merged": "🔀 合并",
        "reopened": "🔄 重新打开",
        "edited": "✏️ 编辑",
        "review_requested": "👀 请求审查",
        "ready_for_review": "📋 准备审查",
    }.get(action, f"📝 {action}")

    card_content = {
        "config": {"wide_screen_mode": True},
        "elements": [
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"{action_text} **Pull Request**\n\n**仓库:** [{repository['name']}]({repository['html_url']})\n**标题:** [{pr['title']}]({pr['html_url']})\n**作者:** {pr['user']['login']}\n**分支:** {pr['head']['ref']} → {pr['base']['ref']}",
                },
            }
        ],
    }

    if pr.get("body"):
        card_content["elements"].append(
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**描述:**\n{pr['body'][:200]}{'...' if len(pr['body']) > 200 else ''}",
                },
            }
        )

    card_content["elements"].append(
        {
            "tag": "action",
            "actions": [
                {
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": "查看PR"},
                    "type": "primary",
                    "url": pr["html_url"],
                }
            ],
        }
    )

    return json.dumps(card_content)


def create_issue_card(payload, action):
    """创建Issue事件卡片"""
    issue = payload["issue"]
    repository = payload["repository"]

    action_text = {
        "opened": "🆕 新建",
        "closed": "✅ 关闭",
        "reopened": "🔄 重新打开",
        "edited": "✏️ 编辑",
        "assigned": "👤 分配",
        "labeled": "🏷️ 添加标签",
    }.get(action, f"📝 {action}")

    card_content = {
        "config": {"wide_screen_mode": True},
        "elements": [
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"{action_text} **Issue**\n\n**仓库:** [{repository['name']}]({repository['html_url']})\n**标题:** [{issue['title']}]({issue['html_url']})\n**作者:** {issue['user']['login']}",
                },
            }
        ],
    }

    if issue.get("body"):
        card_content["elements"].append(
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**描述:**\n{issue['body'][:200]}{'...' if len(issue['body']) > 200 else ''}",
                },
            }
        )

    card_content["elements"].append(
        {
            "tag": "action",
            "actions": [
                {
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": "查看Issue"},
                    "type": "primary",
                    "url": issue["html_url"],
                }
            ],
        }
    )

    return json.dumps(card_content)


def create_release_card(payload, action):
    """创建Release事件卡片"""
    release = payload["release"]
    repository = payload["repository"]

    action_text = {
        "published": "🎉 发布",
        "created": "📦 创建",
        "edited": "✏️ 编辑",
        "deleted": "🗑️ 删除",
    }.get(action, f"📝 {action}")

    card_content = {
        "config": {"wide_screen_mode": True},
        "elements": [
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"{action_text} **新版本**\n\n**仓库:** [{repository['name']}]({repository['html_url']})\n**版本:** [{release['tag_name']}]({release['html_url']})\n**名称:** {release['name'] or release['tag_name']}",
                },
            }
        ],
    }

    if release.get("body"):
        card_content["elements"].append(
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**更新说明:**\n{release['body'][:300]}{'...' if len(release['body']) > 300 else ''}",
                },
            }
        )

    card_content["elements"].append(
        {
            "tag": "action",
            "actions": [
                {
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": "查看Release"},
                    "type": "primary",
                    "url": release["html_url"],
                }
            ],
        }
    )

    return json.dumps(card_content)


@app.route("/webhook", methods=["POST"])
def github_webhook():
    """GitHub Webhook接收端点"""

    # 验证签名
    signature = request.headers.get("X-Hub-Signature-256", "")
    if not verify_github_signature(request.get_data(), signature):
        return jsonify({"error": "Invalid signature"}), 401

    # 获取事件类型
    event_type = request.headers.get("X-GitHub-Event")
    payload = request.get_json()

    if not payload:
        return jsonify({"error": "No payload"}), 400

    print(f"收到GitHub事件: {event_type}")

    message_content = None

    try:
        if event_type == "push":
            # 推送事件
            if payload.get("commits"):  # 忽略空推送
                message_content = create_push_card(payload)

        elif event_type == "pull_request":
            # Pull Request事件
            action = payload.get("action")
            if action in ["opened", "closed", "reopened", "merged"]:
                message_content = create_pr_card(payload, action)

        elif event_type == "issues":
            # Issue事件
            action = payload.get("action")
            if action in ["opened", "closed", "reopened"]:
                message_content = create_issue_card(payload, action)

        elif event_type == "release":
            # Release事件
            action = payload.get("action")
            if action in ["published", "created"]:
                message_content = create_release_card(payload, action)

        elif event_type == "create":
            # 分支/标签创建事件
            ref_type = payload.get("ref_type")
            ref = payload.get("ref")
            repository = payload["repository"]

            if ref_type in ["branch", "tag"]:
                message_content = json.dumps(
                    {
                        "config": {"wide_screen_mode": True},
                        "elements": [
                            {
                                "tag": "div",
                                "text": {
                                    "tag": "lark_md",
                                    "content": f"🌿 **创建{ref_type}**\n\n**仓库:** [{repository['name']}]({repository['html_url']})\n**{ref_type}:** {ref}",
                                },
                            }
                        ],
                    }
                )

        if message_content:
            success = send_feishu_message(message_content)
            if success:
                return jsonify({"status": "success"}), 200
            else:
                return jsonify({"error": "Failed to send message"}), 500
        else:
            return jsonify({"status": "ignored"}), 200

    except Exception as e:
        print(f"处理GitHub事件异常: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/health", methods=["GET"])
def health_check():
    """健康检查端点"""
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()}), 200


@app.route("/", methods=["GET"])
def index():
    """根路径"""
    return (
        jsonify(
            {
                "service": "GitHub-Feishu Bot",
                "status": "running",
                "endpoints": {"webhook": "/webhook", "health": "/health"},
            }
        ),
        200,
    )


if __name__ == "__main__":
    print("GitHub-飞书消息推送服务启动中...")
    print(f"Webhook接收地址: http://1.117.70.65:5000/webhook")
    print(f"健康检查地址: http://1.117.70.65:5000/health")

    # 在生产环境中建议使用WSGI服务器如gunicorn
    app.run(host="0.0.0.0", port=5000, debug=False)
