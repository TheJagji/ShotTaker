/*
 * rust_capture — ShotTaker native capture & diff engine
 *
 * Exposes to Python:
 *   grab_frame(monitor: int) -> (bytes, int, int)
 *       Capture a monitor. Returns (raw RGB bytes, width, height).
 *       monitor: 0 = primary, 1+ = specific index
 *
 *   score_diff(a: bytes, b: bytes, w: int, h: int) -> float
 *       Weighted MAD between two RGB byte buffers (same as frames.py).
 *       0.6 * luminance_diff + 0.4 * colour_diff
 *
 *   mean_luminance(buf: bytes, w: int, h: int) -> float
 *       Average luminance of a frame.
 *
 *   detail_score(buf: bytes, w: int, h: int) -> float
 *       Std-dev of luminance — low = flat/loading screen.
 *
 *   is_letterboxed(buf: bytes, w: int, h: int) -> bool
 *       True if top+bottom bars are near-black.
 *
 *   quality_reject(buf: bytes, w: int, h: int,
 *                  ref_buf: Optional[bytes],
 *                  dark_threshold: float,
 *                  dedupe_threshold: float,
 *                  suppress_dark: bool,
 *                  suppress_loading: bool,
 *                  suppress_letterbox: bool,
 *                  dedupe_enabled: bool) -> Optional[str]
 *       Full quality gate. Returns rejection reason or None.
 *
 *   list_monitors() -> list[dict]
 *       Returns [{index, x, y, width, height, primary}] for all monitors.
 */

use pyo3::prelude::*;
use pyo3::types::PyBytes;

// =============================================================================
// SHARED MATHS  (platform-independent)
// =============================================================================

/// Weighted MAD: 60% luminance + 40% colour, matching frames.py score_diff().
fn diff_score(a: &[u8], b: &[u8]) -> f32 {
    debug_assert_eq!(a.len(), b.len());
    debug_assert_eq!(a.len() % 3, 0);

    let n = (a.len() / 3) as f32;
    let mut lum_sum = 0f32;
    let mut col_sum = 0f32;

    for i in (0..a.len()).step_by(3) {
        let dr = (a[i]     as f32 - b[i]     as f32).abs();
        let dg = (a[i + 1] as f32 - b[i + 1] as f32).abs();
        let db = (a[i + 2] as f32 - b[i + 2] as f32).abs();

        lum_sum += 0.299 * dr + 0.587 * dg + 0.114 * db;
        col_sum += (dr + dg + db) / 3.0;
    }

    0.6 * (lum_sum / n) + 0.4 * (col_sum / n)
}

fn luminance_of(buf: &[u8]) -> f32 {
    let n = (buf.len() / 3) as f32;
    let mut sum = 0f32;
    for i in (0..buf.len()).step_by(3) {
        sum += 0.299 * buf[i] as f32
             + 0.587 * buf[i + 1] as f32
             + 0.114 * buf[i + 2] as f32;
    }
    sum / n
}

fn detail_of(buf: &[u8], w: usize, h: usize) -> f32 {
    let n = (w * h) as f32;
    // mean luminance
    let mean = luminance_of(buf);
    // variance
    let mut var = 0f32;
    for i in (0..buf.len()).step_by(3) {
        let lum = 0.299 * buf[i] as f32
                + 0.587 * buf[i + 1] as f32
                + 0.114 * buf[i + 2] as f32;
        let d = lum - mean;
        var += d * d;
    }
    (var / n).sqrt()
}

fn letterboxed(buf: &[u8], w: usize, h: usize, bar_lum: f32, min_frac: f32) -> bool {
    let row_lum: Vec<f32> = (0..h).map(|row| {
        let mut s = 0f32;
        for col in 0..w {
            let i = (row * w + col) * 3;
            s += 0.299 * buf[i] as f32
               + 0.587 * buf[i + 1] as f32
               + 0.114 * buf[i + 2] as f32;
        }
        s / w as f32
    }).collect();

    let mut top = 0usize;
    while top < h && row_lum[top] < bar_lum { top += 1; }
    let mut bot = 0usize;
    while bot < h && row_lum[h - 1 - bot] < bar_lum { bot += 1; }

    let frac = min_frac;
    (top as f32 / h as f32) >= frac && (bot as f32 / h as f32) >= frac
}

// =============================================================================
// WINDOWS — DXGI DESKTOP DUPLICATION
// =============================================================================
#[cfg(target_os = "windows")]
mod capture {
    use windows::{
        core::*,
        Win32::Graphics::{
            Direct3D::D3D_DRIVER_TYPE_HARDWARE,
            Direct3D11::*,
            Dxgi::*,
            Dxgi::Common::*,
        },
        Win32::Foundation::RECT,
    };

    pub struct Monitor {
        pub index: usize,
        pub x: i32,
        pub y: i32,
        pub width: u32,
        pub height: u32,
        pub primary: bool,
    }

    pub fn list_monitors() -> Vec<Monitor> {
        let mut out = Vec::new();
        unsafe {
            let factory: IDXGIFactory1 = match CreateDXGIFactory1() {
                Ok(f) => f,
                Err(_) => return out,
            };
            let mut adapter_idx = 0u32;
            while let Ok(adapter) = factory.EnumAdapters1(adapter_idx) {
                let mut output_idx = 0u32;
                while let Ok(output) = adapter.EnumOutputs(output_idx) {
                    let mut desc = DXGI_OUTPUT_DESC::default();
                    let desc = match output.GetDesc() {
                        Ok(d) => d,
                        Err(_) => { output_idx += 1; continue; }
                    };
                    let rect: RECT = desc.DesktopCoordinates;
                    let primary = rect.left == 0 && rect.top == 0;
                    out.push(Monitor {
                        index: out.len(),
                        x: rect.left,
                        y: rect.top,
                        width: (rect.right - rect.left) as u32,
                        height: (rect.bottom - rect.top) as u32,
                        primary,
                    });
                    output_idx += 1;
                }
                adapter_idx += 1;
            }
        }
        out
    }

    pub fn grab(monitor_index: usize) -> Result<(Vec<u8>, u32, u32)> {
        unsafe {
            // Create D3D11 device
            let mut device: Option<ID3D11Device> = None;
            let mut context: Option<ID3D11DeviceContext> = None;
            let mut feature_level = windows::Win32::Graphics::Direct3D::D3D_FEATURE_LEVEL_11_0;

            D3D11CreateDevice(
                None,
                D3D_DRIVER_TYPE_HARDWARE,
                None,
                D3D11_CREATE_DEVICE_FLAG(0),
                None,
                D3D11_SDK_VERSION,
                Some(&mut device),
                Some(&mut feature_level),
                Some(&mut context),
            )?;

            let device = device.unwrap();
            let context = context.unwrap();

            // Get DXGI device → adapter → factory → output
            let dxgi_device: IDXGIDevice = device.cast()?;
            let adapter: IDXGIAdapter = dxgi_device.GetAdapter()?;
            let factory: IDXGIFactory1 = adapter.GetParent()?;

            // Find the requested output
            let mut output_idx = 0u32;
            let mut current = 0usize;
            let output = loop {
                let output = match adapter.EnumOutputs(output_idx) {
                    Ok(o) => o,
                    Err(_) => {
                        // Fall back to first output if index out of range
                        adapter.EnumOutputs(0)?
                    }
                };
                if current == monitor_index { break output; }
                current += 1;
                output_idx += 1;
            };

            let output1: IDXGIOutput1 = output.cast()?;
            let duplication = output1.DuplicateOutput(&device)?;

            // Acquire a frame
            let mut frame_info = DXGI_OUTDUPL_FRAME_INFO::default();
            let mut resource: Option<windows::Win32::Graphics::Dxgi::IDXGIResource> = None;

            // Try up to 5 times (first call often returns no frame)
            let texture = 'acquire: {
                for _ in 0..5 {
                    let _ = duplication.ReleaseFrame();
                    match duplication.AcquireNextFrame(100, &mut frame_info, &mut resource) {
                        Ok(_) => {
                            if let Some(ref r) = resource {
                                if let Ok(tex) = r.cast::<ID3D11Texture2D>() {
                                    break 'acquire tex;
                                }
                            }
                        }
                        Err(_) => continue,
                    }
                }
                return Err(Error::from_win32());
            };

            // Get texture description
            let mut desc = D3D11_TEXTURE2D_DESC::default();
            texture.GetDesc(&mut desc);
            let w = desc.Width;
            let h = desc.Height;

            // Create a staging texture we can read from CPU
            let staging_desc = D3D11_TEXTURE2D_DESC {
                Width: w,
                Height: h,
                MipLevels: 1,
                ArraySize: 1,
                Format: DXGI_FORMAT_B8G8R8A8_UNORM,
                SampleDesc: DXGI_SAMPLE_DESC { Count: 1, Quality: 0 },
                Usage: D3D11_USAGE_STAGING,
                BindFlags: D3D11_BIND_FLAG(0).0 as u32,
                CPUAccessFlags: D3D11_CPU_ACCESS_READ.0 as u32,
                MiscFlags: D3D11_RESOURCE_MISC_FLAG(0).0 as u32,
            };
            let mut staging: Option<ID3D11Texture2D> = None;
            device.CreateTexture2D(&staging_desc, None, Some(&mut staging))?;
            let staging = staging.unwrap();

            // Copy GPU → staging
            let src: ID3D11Resource = texture.cast()?;
            let dst: ID3D11Resource = staging.cast()?;
            context.CopyResource(&dst, &src);
            let _ = duplication.ReleaseFrame();

            // Map staging texture → read pixels
            let mut mapped = D3D11_MAPPED_SUBRESOURCE::default();
            context.Map(&dst, 0, D3D11_MAP_READ, 0, Some(&mut mapped))?;

            let pitch = mapped.RowPitch as usize;
            let ptr = mapped.pData as *const u8;
            let mut rgb = Vec::with_capacity((w * h * 3) as usize);

            for row in 0..h as usize {
                let row_ptr = ptr.add(row * pitch);
                for col in 0..w as usize {
                    // BGRA → RGB
                    let b = *row_ptr.add(col * 4);
                    let g = *row_ptr.add(col * 4 + 1);
                    let r = *row_ptr.add(col * 4 + 2);
                    rgb.push(r);
                    rgb.push(g);
                    rgb.push(b);
                }
            }

            context.Unmap(&dst, 0);
            Ok((rgb, w, h))
        }
    }
}

// =============================================================================
// LINUX — X11 stub (to be expanded)
// =============================================================================
#[cfg(target_os = "linux")]
mod capture {
    pub struct Monitor {
        pub index: usize,
        pub x: i32,
        pub y: i32,
        pub width: u32,
        pub height: u32,
        pub primary: bool,
    }

    pub fn list_monitors() -> Vec<Monitor> {
        // TODO: implement via XRandR
        vec![Monitor { index: 0, x: 0, y: 0, width: 1920, height: 1080, primary: true }]
    }

    pub fn grab(_monitor_index: usize) -> Result<(Vec<u8>, u32, u32), String> {
        Err("Linux capture not yet implemented — falling back to mss".to_string())
    }
}

// =============================================================================
// macOS — CoreGraphics stub (to be expanded)
// =============================================================================
#[cfg(target_os = "macos")]
mod capture {
    pub struct Monitor {
        pub index: usize,
        pub x: i32,
        pub y: i32,
        pub width: u32,
        pub height: u32,
        pub primary: bool,
    }

    pub fn list_monitors() -> Vec<Monitor> {
        vec![Monitor { index: 0, x: 0, y: 0, width: 1920, height: 1080, primary: true }]
    }

    pub fn grab(_monitor_index: usize) -> Result<(Vec<u8>, u32, u32), String> {
        Err("macOS capture not yet implemented — falling back to mss".to_string())
    }
}

// =============================================================================
// PYTHON BINDINGS
// =============================================================================

/// Capture a monitor. Returns (rgb_bytes, width, height).
/// monitor: 0 = primary, 1+ = specific index.
#[pyfunction]
fn grab_frame(py: Python<'_>, monitor: usize) -> PyResult<(Py<PyBytes>, u32, u32)> {
    #[cfg(target_os = "windows")]
    {
        capture::grab(monitor)
            .map(|(buf, w, h)| (PyBytes::new(py, &buf).into(), w, h))
            .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))
    }
    #[cfg(not(target_os = "windows"))]
    {
        capture::grab(monitor)
            .map(|(buf, w, h)| (PyBytes::new(py, &buf).into(), w, h))
            .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e))
    }
}

/// Weighted MAD between two RGB byte buffers. Higher = more change.
#[pyfunction]
fn score_diff(_py: Python<'_>, a: &[u8], b: &[u8]) -> PyResult<f32> {
    if a.len() != b.len() {
        return Err(pyo3::exceptions::PyValueError::new_err(
            "Buffers must be the same length"
        ));
    }
    Ok(diff_score(a, b))
}

/// Average luminance of an RGB frame.
#[pyfunction]
fn mean_luminance(_py: Python<'_>, buf: &[u8]) -> PyResult<f32> {
    Ok(luminance_of(buf))
}

/// Std-dev of luminance. Low = flat/loading screen.
#[pyfunction]
fn detail_score(_py: Python<'_>, buf: &[u8], w: usize, h: usize) -> PyResult<f32> {
    Ok(detail_of(buf, w, h))
}

/// True if top+bottom bars are near-black (letterboxed cutscene/loading).
#[pyfunction]
fn is_letterboxed(_py: Python<'_>, buf: &[u8], w: usize, h: usize) -> PyResult<bool> {
    Ok(letterboxed(buf, w, h, 16.0, 0.10))
}

/// Full quality gate. Returns rejection reason string or None.
#[pyfunction]
#[allow(clippy::too_many_arguments)]
fn quality_reject(
    _py: Python<'_>,
    buf: &[u8],
    w: usize,
    h: usize,
    ref_buf: Option<&[u8]>,
    dark_threshold: f32,
    dedupe_threshold: f32,
    suppress_dark: bool,
    suppress_loading: bool,
    suppress_letterbox: bool,
    dedupe_enabled: bool,
) -> PyResult<Option<String>> {
    if suppress_dark && luminance_of(buf) < dark_threshold {
        return Ok(Some("dark".to_string()));
    }
    if suppress_loading && detail_of(buf, w, h) < 6.0 {
        return Ok(Some("low-detail".to_string()));
    }
    if suppress_letterbox && letterboxed(buf, w, h, 16.0, 0.10) {
        return Ok(Some("letterbox".to_string()));
    }
    if dedupe_enabled {
        if let Some(ref_frame) = ref_buf {
            if buf.len() == ref_frame.len() && diff_score(buf, ref_frame) < dedupe_threshold {
                return Ok(Some("duplicate".to_string()));
            }
        }
    }
    Ok(None)
}

/// List all monitors: [{index, x, y, width, height, primary}]
#[pyfunction]
fn list_monitors(py: Python<'_>) -> PyResult<Vec<PyObject>> {
    use pyo3::types::PyDict;
    let monitors = capture::list_monitors();
    monitors.iter().map(|m| {
        let d = PyDict::new(py);
        d.set_item("index", m.index)?;
        d.set_item("x", m.x)?;
        d.set_item("y", m.y)?;
        d.set_item("width", m.width)?;
        d.set_item("height", m.height)?;
        d.set_item("primary", m.primary)?;
        Ok(d.into())
    }).collect()
}

// =============================================================================
// MODULE REGISTRATION
// =============================================================================
#[pymodule]
fn rust_capture(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(grab_frame, m)?)?;
    m.add_function(wrap_pyfunction!(score_diff, m)?)?;
    m.add_function(wrap_pyfunction!(mean_luminance, m)?)?;
    m.add_function(wrap_pyfunction!(detail_score, m)?)?;
    m.add_function(wrap_pyfunction!(is_letterboxed, m)?)?;
    m.add_function(wrap_pyfunction!(quality_reject, m)?)?;
    m.add_function(wrap_pyfunction!(list_monitors, m)?)?;
    m.add("__version__", "0.1.0")?;
    m.add("__backend__", if cfg!(target_os = "windows") { "dxgi" }
                         else if cfg!(target_os = "linux") { "x11-stub" }
                         else { "coregraphics-stub" })?;
    Ok(())
}
