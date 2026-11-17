# Brain_Standard CLI in a container, for machines without Python 3.11+.
# The image holds only the brain package (tools/brain/). Your brain, the folder with
# brain.toml and vault/, is mounted at run time and never goes into the image:
#
#   docker run --rm -v "$PWD:/brain" dfat243/brain_standard check
#   docker run --rm -v "$PWD:/brain" --user "$(id -u):$(id -g)" dfat243/brain_standard capture "…"
#
# The image runs as an unprivileged user (uid 10001), never as root. On Linux, pass
# --user to write into your brain with your own uid; Docker Desktop does not need it.
#
# The base image is pinned by digest, so a rebuild cannot silently pick up a changed
# image. To update it: docker buildx imagetools inspect python:3.12-slim, copy the
# index digest here, and say so in the CHANGELOG.
FROM python:3.12-slim@sha256:5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b

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

# An unprivileged user with no home and no login shell; the package stays owned by root
# and read-only to it.
RUN useradd --system --uid 10001 --user-group --no-create-home --shell /usr/sbin/nologin brain
USER 10001:10001

# The CLI finds the brain by walking up from here to the folder that holds brain.toml.
WORKDIR /brain
ENTRYPOINT ["python", "-m", "brain"]
CMD ["--help"]
