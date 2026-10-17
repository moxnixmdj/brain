# Browser availability: obtained and executing, blocked at page load

## The previous claim, corrected

Earlier this session I reported "there is no browser in this environment"
and treated browser work as impossible. That was wrong in an important way.

It was true that no browser was installed. It was false that none could be
obtained. The lesson is the same one the real repositories taught: I checked
`command -v`, found nothing, and concluded. I never asked whether one could
be brought in.

## A real Chromium 153 now runs here

    Chromium 153.0.8010.0
    (209MB ELF, executes, reports its version)

Recipe, fully reproducible, using only allow-listed hosts:

    mkdir browser_build && cd browser_build
    npm install @sparticuz/chromium          # registry.npmjs.org
    node -e "extract chromium.br with zlib.brotliDecompressSync"
    tar -xf al2023.tar                        # the shared libraries
    LD_LIBRARY_PATH=./al2023/lib ./chromium --version

`@sparticuz/chromium` is normally used for AWS Lambda and ships the binary
brotli-compressed along with its Amazon Linux shared libraries. Extracting
those and pointing LD_LIBRARY_PATH at them is enough to make it start.
Node's zlib does the decompression; no extra tools needed.

## What does NOT work, and what was tried

Loading a page hangs. The GPU process fails initialisation and the browser
then waits indefinitely:

    ANGLE Display::initialize error: Internal Vulkan error (-3)
    eglInitialize SwANGLE failed with error EGL_NOT_INITIALIZED
    Initialization of all (1) EGL display types failed
    Exiting GPU process due to errors during initialization
    -> hangs until killed

Eight flag combinations tried, all failing:

    --headless=old --disable-gpu                                  exit 124 (hang)
    --headless=new --disable-gpu                                  exit 124
    --disable-gpu --use-gl=disabled --disable-software-rasterizer exit 124
    --disable-gpu --use-gl=angle --use-angle=swiftshader          exit 133 (crash)
    --disable-gpu --in-process-gpu                                exit 133
    --disable-gpu --disable-features=Vulkan --use-angle=swiftshader  exit 124
    --disable-gpu --disable-features=VizDisplayCompositor,Vulkan  exit 124
    --disable-gl-drawing-for-tests --no-zygote                    exit 124
    --single-process --no-zygote                                  exit 133

Ruled out as the cause:
    /dev/shm    2.0G tmpfs, fine
    seccomp     disabled (Seccomp: 0)
    libraries   libnspr4 et al resolved once LD_LIBRARY_PATH is set
    swiftshader extracted from the package, still fails

So the blocker is graphics initialisation. The binary starts, loads its
libraries, and dies in the GPU process before it can composite a frame.

## What this does and does not mean

It does NOT mean browser work is possible here. No page has rendered. No
JavaScript has run. Nothing has been clicked. The browser capability remains
untested against a real page.

It DOES mean the "no browser exists" obstacle is gone. What remains is an
environment limitation, not an absence — and environment limitations can
differ on another machine. On a host with working EGL/GL libraries, or with
the right ANGLE backend available, this same recipe should render.

## Next steps, in order

1. On a machine with functioning graphics libraries, run the recipe and
   confirm --dump-dom renders and executes JavaScript.
2. Only then write the browser driver: CDP over --remote-debugging-port,
   wired into the loop like htmlform_read_v1 but driving real clicks and
   real DOM.
3. Keep the HTTP-level form work as the fallback for environments where a
   browser cannot start. It is not a substitute, but it is something.
