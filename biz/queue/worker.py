import os
import traceback
from datetime import datetime

from biz.entity.codeReviewEntity import MergeEntity, PushEntity
from biz.event.eventManager import eventManager
from biz.gitlab.gitlabHandler import filter_changes, MergeRequestHandler, PushHandler
from biz.utils.codeReview import CodeReviewer
from biz.report import notifier
from biz.utils.log import logger



def handle_push_event(webhook_data: dict, gitlab_token: str, gitlab_url: str, gitlab_url_slug: str):
    push_review_enabled = os.environ.get('PUSH_REVIEW_ENABLED', '0') == '1'
    try:
        handler = PushHandler(webhook_data, gitlab_token, gitlab_url)
        logger.info('Push Hook event received')
        commits = handler.get_push_commits()
        if not commits:
            logger.error('Failed to get commits')
            return

        review_result = None
        score = 0
        if push_review_enabled:
            # 获取PUSH的changes
            changes = handler.get_push_changes()
            logger.info('changes: %s', changes)
            changes = filter_changes(changes)
            if not changes:
                logger.info('未检测到PUSH代码的修改,修改文件可能不满足SUPPORTED_EXTENSIONS。')
            review_result = "关注的文件没有修改"

            if len(changes) > 0:
                commits_text = ';'.join(commit.get('message', '').strip() for commit in commits)
                review_result = CodeReviewer().review_and_strip_code(str(changes), commits_text)
                score = CodeReviewer.parse_review_score(review_text=review_result)
            # 将review结果提交到Gitlab的 notes
            handler.add_push_notes(f'Auto Review Result: \n{review_result}')

        eventManager['push_reviewed'].send(PushEntity(
            project_name=webhook_data['project']['name'],
            author=webhook_data['user_username'],
            branch=webhook_data['project']['default_branch'],
            updated_at=int(datetime.now().timestamp()),  # 当前时间
            commits=commits,
            score=score,
            review_result=review_result,
            url_slug=gitlab_url_slug,
        ))

    except Exception as e:
        error_message = f'服务出现未知错误: {str(e)}\n{traceback.format_exc()}'
        notifier.sendReport(content=error_message)
        logger.error('出现未知错误: %s', error_message)


def handle_merge_request_event(webhook_data: dict, gitlab_token: str, gitlab_url: str, gitlab_url_slug: str):
    try:
        # 解析Webhook数据
        handler = MergeRequestHandler(webhook_data, gitlab_token, gitlab_url)
        logger.info('Merge Request Hook event received')

        # if handler.action not in ['open', 'update']:
        #     logger.info(f"Merge Request Hook event, action={handler.action}, ignored.")
        #     return

        # 仅仅在MR创建或更新时进行Code Review
        # 获取Merge Request的changes
        changes = handler.get_merge_request_changes()
        logger.info('changes: %s', changes)
        changes = filter_changes(changes)
        if not changes:
            logger.info('未检测到有关代码的修改,修改文件可能不满足SUPPORTED_EXTENSIONS。')
            return

        # 获取Merge Request的commits
        commits = handler.get_merge_request_commits()
        if not commits:
            logger.error('Failed to get commits')
            return

        # review 代码
        commits_text = ';'.join(commit['title'] for commit in commits)
        review_result = CodeReviewer().review_and_strip_code(str(changes), commits_text)

        # 将review结果提交到Gitlab的 notes
        handler.add_merge_request_notes(f'Auto Review Result: \n{review_result}')

        # dispatch merge_request_reviewed event
        eventManager['merge_request_reviewed'].send(
            MergeEntity(
                project_name=webhook_data['title'],
                author=webhook_data['author']['username'],
                source_branch=webhook_data['source_branch'],
                target_branch=webhook_data['target_branch'],
                updated_at=webhook_data['merged_at'],
                commits=commits,
                score=CodeReviewer.parse_review_score(review_text=review_result),
                url=webhook_data['web_url'],
                review_result=review_result,
                url_slug=gitlab_url_slug,
            )
        )

    except Exception as e:
        error_message = f'AI Code Review 服务出现未知错误: {str(e)}\n{traceback.format_exc()}'
        notifier.sendReport(content=error_message)
        logger.error('出现未知错误: %s', error_message)

