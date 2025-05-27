import abc
import os
import re
from typing import Dict, Any, List

import yaml

from biz.llm.deepseek import DeepSeekClient
from biz.utils.log import logger
from biz.utils.tokenUtil import count_tokens, truncate_text_by_tokens


class BaseReviewer(abc.ABC):

    def __init__(self, prompt_key: str):
        self.client = DeepSeekClient()
        self.prompts = self._load_prompts()

    def _load_prompts(self) -> Dict[str, Any]:
        system_prompt = """
        你是一位资深的软件开发工程师，专注于代码的规范性、功能性、安全性和稳定性。本次任务是对员工的代码进行审查，具体要求如下：

        ### 代码审查目标：
        1. 功能实现的正确性与健壮性（40分）： 确保代码逻辑正确，能够处理各种边界情况和异常输入。
        2. 安全性与潜在风险（30分）：检查代码是否存在安全漏洞（如SQL注入、XSS攻击等），并评估其潜在风险。
        3. 是否符合最佳实践（20分）：评估代码是否遵循行业最佳实践，包括代码结构、命名规范、注释清晰度等。
        4. 性能与资源利用效率（5分）：分析代码的性能表现，评估是否存在资源浪费或性能瓶颈。
        5. Commits信息的清晰性与准确性（5分）：检查提交信息是否清晰、准确，是否便于后续维护和协作。
        
        ### 输出格式:
        请以Markdown格式输出代码审查报告，并包含以下内容：
        1. 问题描述和优化建议(如果有)：列出代码中存在的问题，简要说明其影响，并给出优化建议。
        2. 评分明细：为每个评分标准提供具体分数。
        3. 总分：格式为“总分:XX分”（例如：总分:80分），确保可通过正则表达式 r"总分[:：]\\s*(\\d+)分?"） 解析出总分。
        
        ### 特别说明：
        整个评论要保持professional风格
        评论时请使用标准的工程术语，保持专业严谨。
        """
        user_prompt = """
        以下是某位员工向 GitLab 代码库提交的代码，请以professional风格审查以下代码。

        代码变更内容：
        {diffs_text}
        
        提交历史(commits)：
        {commits_text}
        """

        return {
            "system_message": {"role": "system", "content": system_prompt},
            "user_message": {"role": "user", "content": user_prompt},
        }

    def call_llm(self, messages: List[Dict[str, Any]]) -> str:
        logger.info(f"向 AI 发送代码 Review 请求, messages: {messages}")
        review_result = self.client.completions(messages=messages)
        logger.info(f"收到 AI 返回结果: {review_result}")
        return review_result

    @abc.abstractmethod
    def review_code(self, *args, **kwargs) -> str:
        """抽象方法，子类必须实现"""
        pass


class CodeReviewer(BaseReviewer):
    """代码 Diff 级别的审查"""

    def __init__(self):
        super().__init__("code_review_prompt")

    def review_and_strip_code(self, changes_text: str, commits_text: str = "") -> str:
        # 如果超长，取前REVIEW_MAX_TOKENS个token
        review_max_tokens = int(os.getenv("REVIEW_MAX_TOKENS", 10000))
        # 如果changes为空,打印日志
        if not changes_text:
            logger.info("代码为空, diffs_text = %", str(changes_text))
            return "代码为空"

        # 计算tokens数量，如果超过REVIEW_MAX_TOKENS，截断changes_text
        tokens_count = count_tokens(changes_text)
        if tokens_count > review_max_tokens:
            changes_text = truncate_text_by_tokens(changes_text, review_max_tokens)

        review_result = self.review_code(changes_text, commits_text).strip()
        if review_result.startswith("```markdown") and review_result.endswith("```"):
            return review_result[11:-3].strip()
        return review_result

    def review_code(self, diffs_text: str, commits_text: str = "") -> str:
        """Review 代码并返回结果"""
        messages = [
            self.prompts["system_message"],
            {
                "role": "user",
                "content": self.prompts["user_message"]["content"].format(
                    diffs_text=diffs_text, commits_text=commits_text
                ),
            },
        ]
        return self.call_llm(messages)

    @staticmethod
    def parse_review_score(review_text: str) -> int:
        """解析 AI 返回的 Review 结果，返回评分"""
        if not review_text:
            return 0
        match = re.search(r"总分[:：]\s*(\d+)分?", review_text)
        return int(match.group(1)) if match else 0

