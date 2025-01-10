import multiprocessing

import uvicorn

from config.main_config import WEB_APP_PORT, WEB_APP_HOST, LOG_LEVEL

if __name__ == "__main__":

    workers = multiprocessing.cpu_count() * 2 + 1


    uvicorn.run("web.app:app", host=WEB_APP_HOST, port=WEB_APP_PORT, workers=workers, log_level=LOG_LEVEL.lower())