# Brain_Standard CLI in a container, for machines without Python 3.11+.
# The image holds only the brain package (tools/brain/). Your brain, the folder with
# brain.toml and vault/, is mounted at run time and never goes into the image:
#
#   docker run --rm -v "$PWD:/brain" dfat243/brain_standard check
#   docker run --rm -v "$PWD:/brain" --user "$(id -u):$(id -g)" dfat243/brain_standard capture "…"
#
# --user keeps new files owned by you on Linux; Docker Desktop does not need it.
FROM python:3.12-slim

LABEL org.opencontainers.image.title="Brain_Standard" \
      org.opencontainers.image.description="The brain CLI: a second brain in Markdown and git" \
      org.opencontainers.image.source="https://github.com/DaveTran243/Brain_Standard"

# Same as bin/brain: put tools/ on the path and run the package.
# No bytecode files, so a non-root --user never needs to write under /opt.
ENV PYTHONPATH=/opt/brain/tools \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONUTF8=1

COPY tools/ /opt/brain/tools/

# The CLI finds the brain by walking up from here to the folder that holds brain.toml.
WORKDIR /brain
ENTRYPOINT ["python", "-m", "brain"]
CMD ["--help"]
