import uuid
from datetime import datetime


# 模拟obs客户端 真实项目用华为obs sdk
class MockOBSClient:
    """模拟华为obs客户端，开发环境使用"""

    def __init__(self, bucket_name):
        self.bucket_name = bucket_name
        self.files = {}  # 用字典模拟存储，key是文件路径，value是文件内容

    def generate_presigned_upload_url(self, object_key: str, expires: int = 3600):
        """
        生成预签名URL
        真实项目调用OBS SDK的create_digned_url方法
        ：param object_key:文件在桶里的路径，如avatars/user123.jpg
        :param expires:URL有效期（秒），默认1小时
        """
        return f"https://{self.bucket_name}.obs.cn-south-1.myhuaweicloud.com{object_key}?sign=upload_token&expires={expires}"

    def generate_presigned_download_url(self, object_key: str, expiers: int = 3600):
        """生成预签名下载URL"""
        return f"https://{self.bucket_name}.obs.cn-south-1.myhuaweicloud.com/{object_key}?sign=download_token&expires={expiers}"

    def delete_object(self, object_key: str):
        """删除OBS上面的文件"""
        if object_key in self.files:
            del self.files[object_key]
            print(f"[OBBS模拟]删除文件：{object_key}")
            return True
        return False

    def object_exists(self, object_key: str):
        """检查文件是否存在"""
        return object_key in self.files


# 初始化OBS客户端（真实项目从环境变量中读取配置）
obs_client = MockOBSClient(bucket_name="exam-system-bucket")


def generate_unique_key(user_identifier: str, original_filename: str, folder: str = "avatars"):
    """
    生成唯一的文件存储路径
    格式：avatars/用户表示 ——随机UUID.扩展名
    """
    ext = original_filename.rsplit(".", 1)[-1] if "." in original_filename else "jpg"
    unique_name = f"{user_identifier}_{uuid.uuid4().hex[:8]}.{ext}"
    return f"{folder}/{unique_name}"


def get_upload_url(user_identifier: str, filename: str):
    """
    给前端返回一个预签名上传URL
    前端用这个URL直接上传文件到OBS，不经过后端服务器
    """
    object_key = generate_unique_key(user_identifier, filename)
    upload_url = obs_client.generate_presigned_upload_url(object_key)
    return {
        "upload_url": upload_url,
        "object_key": object_key,
        "expires_in": 3600
    }


def get_file_url(object_key: str):
    """根据文件key获取访问url"""
    return obs_client.generate_presigned_download_url(object_key)


def delete_file(object_key: str):
    """删除OBS上面的文件"""
    return obs_client.delete_object(object_key)
