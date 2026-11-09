// Explicit, local browser capability inspection. No network calls or persistent identifiers.
// Capability discovery does NOT request a GPUDevice or execute any compute work.
export async function inspectResources(navigatorRef = navigator, createCanvas = () => document.createElement('canvas')) {
  const result = {
    logicalProcessors: Number.isFinite(navigatorRef.hardwareConcurrency) ? navigatorRef.hardwareConcurrency : null,
    approximateRamGiB: Number.isFinite(navigatorRef.deviceMemory) ? navigatorRef.deviceMemory : null,
    webgl: {available:false}, webgpu:{available:false}, battery:null,
    temperature:null, fanRPM:null, gpuPowerWatts:null, totalVramGiB:null,
  };
  try {
    const canvas = createCanvas();
    const gl = canvas.getContext('webgl2', {powerPreference:'low-power', failIfMajorPerformanceCaveat:true});
    if (gl) {
      result.webgl = {
        available:true,
        maxTextureSize:gl.getParameter(gl.MAX_TEXTURE_SIZE),
        maxRenderbufferSize:gl.getParameter(gl.MAX_RENDERBUFFER_SIZE)
      };
      gl.getExtension('WEBGL_lose_context')?.loseContext();
    }
  } catch { /* Browser refused a graphics context. No diagnostic failure propagates. */ }
  try {
    if (navigatorRef.gpu && globalThis.isSecureContext) {
      const adapter = await navigatorRef.gpu.requestAdapter({powerPreference:'low-power'});
      if (adapter) {
        result.webgpu = {
          available:true,
          // These are browser-exposed allocation ceilings, never total VRAM or thermal readings.
          maxBufferMiB:Math.floor(Number(adapter.limits.maxBufferSize || 0) / 1048576),
          maxStorageBindingMiB:Math.floor(Number(adapter.limits.maxStorageBufferBindingSize || 0) / 1048576),
          maxWorkgroupInvocations:Number(adapter.limits.maxComputeInvocationsPerWorkgroup || 0),
          vendor:adapter.info?.vendor || null,
        };
      }
    }
  } catch { /* WebGPU can be disabled by browser policy, drivers, or settings. */ }
  try {
    if (typeof navigatorRef.getBattery === 'function') {
      const b = await navigatorRef.getBattery();
      result.battery = {charging:!!b.charging, percentage:Math.round(b.level * 100)};
    }
  } catch { /* Battery is optional and privacy-restricted. */ }
  return result;
}

// A tiny, user-triggered local proof of WebGPU execution. No Cat work, uploads or persistent allocations.
export async function proveWebGpu(navigatorRef = navigator) {
  if (!globalThis.isSecureContext || !navigatorRef.gpu) throw new Error('WebGPU requires a compatible secure-context browser');
  const adapter = await navigatorRef.gpu.requestAdapter({powerPreference:'low-power'});
  if (!adapter) throw new Error('No WebGPU adapter was offered by this browser');
  const device = await adapter.requestDevice();
  try {
    // Four 32-bit integers (16 bytes); no substantial GPU load or benchmark.
    const usage = globalThis.GPUBufferUsage;
    if (!usage) throw new Error('WebGPU buffer support is unavailable');
    const source = device.createBuffer({size:16,usage:usage.STORAGE | usage.COPY_SRC});
    const readback = device.createBuffer({size:16,usage:usage.COPY_DST | usage.MAP_READ});
    try {
      const shader = device.createShaderModule({code:`@group(0) @binding(0) var<storage, read_write> numbers: array<u32>;
@compute @workgroup_size(4) fn main(@builtin(local_invocation_index) i:u32) { numbers[i] = (i + 1u) * 7u; }`});
      const pipeline = device.createComputePipeline({layout:'auto',compute:{module:shader,entryPoint:'main'}});
      const bindGroup = device.createBindGroup({layout:pipeline.getBindGroupLayout(0),entries:[{binding:0,resource:{buffer:source}}]});
      const encoder = device.createCommandEncoder();
      const pass = encoder.beginComputePass();pass.setPipeline(pipeline);pass.setBindGroup(0,bindGroup);pass.dispatchWorkgroups(1);pass.end();
      encoder.copyBufferToBuffer(source,0,readback,0,16);
      device.queue.submit([encoder.finish()]);
      await readback.mapAsync(globalThis.GPUMapMode.READ);
      const result = Array.from(new Uint32Array(readback.getMappedRange().slice(0)));
      readback.unmap();
      if (result.join(',') !== '7,14,21,28') throw new Error('GPU proof returned unexpected values');
      return result;
    } finally {source.destroy();readback.destroy();}
  } finally {device.destroy();}
}
