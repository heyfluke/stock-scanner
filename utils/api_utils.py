class APIUtils:
    @staticmethod
    def format_api_url(base_url: str) -> str:
        """
        格式化 API URL

        /结尾忽略v1版本，#结尾强制使用输入地址
        
        Args:
            base_url: 基础 API URL
            
        Returns:
            str: 格式化后的完整 API URL
        """
        if not base_url:
            return ""
            
        # 如果已经是完整的chat/completions端点，直接返回
        if base_url.endswith('/chat/completions') or base_url.endswith('/chat/completions/'):
            return base_url.rstrip('/')
            
        if base_url.endswith('/'):
            return f"{base_url}chat/completions"
        elif base_url.endswith('#'):
            return base_url.replace('#', '')
        else:
            return f"{base_url}/v1/chat/completions"