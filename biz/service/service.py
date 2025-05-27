import json
import os
from urllib.parse import urlparse

from dotenv import load_dotenv
from flask import Flask, request, jsonify

from biz.gitlab.gitlabHandler import slugify_url
from biz.queue.worker import handle_merge_request_event
from biz.llm.deepseek import DeepSeekClient
from biz.utils.log import logger
from biz.utils.queue import handle_queue
load_dotenv("conf/.env")
api_app = Flask(__name__)


push_review_enabled = os.environ.get('PUSH_REVIEW_ENABLED', '0') == '1'

def handle_gitlab(data):
    logger.info(f"获取提交信息2.{data}")
    gitlab_url = os.getenv('GITLAB_URL') or request.headers.get('X-Gitlab-Instance')
    logger.info("获取提交信息3.")
    logger.info(gitlab_url)
    if not gitlab_url:
        repository = data.get('repository')
        if not repository:
            return jsonify({'message': 'Missing GitLab URL'}), 400
        homepage = repository.get("homepage")
        if not homepage:
            return jsonify({'message': 'Missing GitLab URL'}), 400
        try:
            parsed_url = urlparse(homepage)
            gitlab_url = f"{parsed_url.scheme}://{parsed_url.netloc}/"
        except Exception as e:
            return jsonify({"error": f"Failed to parse homepage URL: {str(e)}"}), 400

    gitlab_token = os.getenv('GITLAB_ACCESS_TOKEN') or request.headers.get('X-Gitlab-Token')
    logger.info(gitlab_token)
    if not gitlab_token:
        return jsonify({'message': 'Missing GitLab access token'}), 400

    gitlab_url_slug = slugify_url(gitlab_url)

    logger.info(f'Payload: {json.dumps(data)}')

    handle_queue(handle_merge_request_event, data, gitlab_token, gitlab_url, gitlab_url_slug)
    # 立马返回响应
    return jsonify(
        {'message': f'Request received(object_kind=merge), will process asynchronously.'}), 200

def check_deepseek():

    required_keys = ["DEEPSEEK_API_KEY", "DEEPSEEK_API_MODEL"]
    missing_keys = [key for key in required_keys if not os.getenv(key)]

    if missing_keys:
        logger.error(f"deepseek缺少必要的变量: {', '.join(missing_keys)}")
    else:
        logger.info(f"deepseek配置完成")

def check_deepseek_connection():
    client = DeepSeekClient()
    logger.info(f"正在检查 LLM 供应商的连接...")
    if client.ping():
        logger.info("LLM 可以连接成功。")
    else:
        logger.error("LLM连接可能有问题，请检查配置项。")

if __name__ == '__main__':
    logger.info("检查配置项...")
    check_deepseek()
    check_deepseek_connection()
    logger.info("配置项检查完成。")