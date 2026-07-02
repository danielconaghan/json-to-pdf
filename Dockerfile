FROM public.ecr.aws/lambda/python:3.12

# matplotlib writes a font cache on first import; /tmp is the only
# writable path at Lambda runtime.
ENV MPLCONFIGDIR=/tmp/mpl

# Install pdfgen and the API dependencies into site-packages from a build
# staging dir, keeping the task root free of a shadowing source copy.
COPY pyproject.toml /tmp/build/
COPY pdfgen/ /tmp/build/pdfgen/
RUN pip install --no-cache-dir "/tmp/build/[api]" && rm -rf /tmp/build

# Bundled brand assets (logos referenced by config paths resolve relative
# to the task root) and the handler package.
COPY assets/ ${LAMBDA_TASK_ROOT}/assets/
COPY api/ ${LAMBDA_TASK_ROOT}/api/

CMD ["api.handler.lambda_handler"]
