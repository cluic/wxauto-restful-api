from wxautox4 import WxParam

class Settings:
    WECHAT_APP_PATH: str = "C:/Program Files/WeChat/WeChat.exe"
    DEFAULT_SAVE_PATH: str = "./wxauto"
    LISTENER_EXCUTOR_WORKERS: int = 4

    @staticmethod
    def apply():
        WxParam.DEFAULT_SAVE_PATH = Settings.DEFAULT_SAVE_PATH
        WxParam.LISTENER_EXCUTOR_WORKERS = Settings.LISTENER_EXCUTOR_WORKERS
