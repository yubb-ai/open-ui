import uvicorn

log_config = uvicorn.config.LOGGING_CONFIG
default_format = "%(asctime)s | %(levelname)s | %(message)s"
access_format = (
    r"%(asctime)s | %(levelname)s | %(client_addr)s: %(request_line)s %(status_code)s"
)

log_config["formatters"]["default"]["fmt"] = default_format
log_config["formatters"]["access"]["fmt"] = access_format


def run_open_webui():
    uvicorn.run(
        "open_webui.main:app",
        host="127.0.0.1",
        port=8080,
        forwarded_allow_ips="*",  # Allows connections from any IP when behind a proxy
        reload=True,  # Enables automatic reloading on code changes (for development)
    )


if __name__ == "__main__":
    run_open_webui()
