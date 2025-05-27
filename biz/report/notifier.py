from biz.report.dingtalk import DingTalkNotifier


def sendReport(content, msg_type='text', title="代码检查报告", is_at_all=False, project_name=None, url_slug=None):
    # 钉钉推送
    dingtalk_notifier = DingTalkNotifier()
    dingtalk_notifier.send_message(content=content, msg_type=msg_type, title=title, is_at_all=is_at_all,
                          project_name=project_name, url_slug=url_slug)

