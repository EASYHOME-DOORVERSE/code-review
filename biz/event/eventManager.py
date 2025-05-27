from blinker import Signal

from biz.entity.codeReviewEntity import MergeEntity, PushEntity
from biz.report import notifier

# 定义全局事件管理器（事件信号）
eventManager = {
    "merge_request_reviewed": Signal(),
    "push_reviewed": Signal(),
}


# 定义事件处理函数
def on_merge_request_reviewed(merge_review_entity: MergeEntity):
    # 发送IM消息通知
    im_msg = f"""
### {merge_review_entity.project_name}: Merge Request
#### 合并请求信息:
- **提交者:** {merge_review_entity.author}
- **源分支**: {merge_review_entity.source_branch}
- **目标分支**: {merge_review_entity.target_branch}
- **更新时间**: {merge_review_entity.updated_at}
- **提交信息:** {merge_review_entity.commit_messages}
- [查看合并详情]({merge_review_entity.url})
- **AI Review 结果:** 

{merge_review_entity.review_result}
    """
    notifier.sendReport(content=im_msg, msg_type='markdown', title='Merge Request Review',
                               project_name=merge_review_entity.project_name,
                               url_slug=merge_review_entity.url_slug)



def on_push_reviewed(entity: PushEntity):
    # 发送IM消息通知
    im_msg = f"### 🚀 {entity.project_name}: Push\n\n"
    im_msg += "#### 提交记录:\n"

    for commit in entity.commits:
        message = commit.get('message', '').strip()
        author = commit.get('author', 'Unknown Author')
        timestamp = commit.get('timestamp', '')
        url = commit.get('url', '#')
        im_msg += (
            f"- **提交信息**: {message}\n"
            f"- **提交者**: {author}\n"
            f"- **时间**: {timestamp}\n"
            f"- [查看提交详情]({url})\n\n"
        )

    if entity.review_result:
        im_msg += f"#### AI Review 结果: \n {entity.review_result}\n\n"
    notifier.sendReport(content=im_msg, msg_type='markdown',
                               title=f"{entity.project_name} Push Event", project_name=entity.project_name,
                               url_slug=entity.url_slug)



# 连接事件处理函数到事件信号
eventManager["merge_request_reviewed"].connect(on_merge_request_reviewed)
eventManager["push_reviewed"].connect(on_push_reviewed)
