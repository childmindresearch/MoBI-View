/**
 * Channel Color Configuration for MoBI-View
 * 
 * This file defines how channels are colored in the visualization.
 * Colors are assigned based on pattern matching against channel names.
 * 
 * HOW IT WORKS:
 * 1. When a channel is first seen, we check if its name matches any pattern
 * 2. If a pattern matches, we use that color group
 * 3. If no pattern matches, we generate a color based on a hash of the name
 * 
 * COLOR FORMAT:
 * - Use HSL format: hsl(hue, saturation%, lightness%)
 * - Hue: 0-360 (color wheel position)
 * - Saturation: 0-100% (color intensity, 0=gray, 100=vivid)
 * - Lightness: 0-100% (brightness, 0=black, 50=normal, 100=white)
 * 
 * PATTERN MATCHING:
 * - Patterns can use wildcards (*, ?) or regular expressions
 * - Matching is case-insensitive
 * - First matching pattern wins
 */

/**
 * Pre-defined color groups for common channel name patterns.
 * 
 * Each entry has:
 * - pattern: String or RegExp to match against channel names
 * - color: HSL color string
 * - description: Human-readable explanation of what this matches
 * 
 * ORDER MATTERS: Patterns are checked in order, first match wins!
 */
const COLOR_GROUPS = [
  // ========== EEG CHANNELS ==========
  
  // Frontal channels (blue tones)
  { pattern: /^(fp|af|f)\d+$/i, color: 'hsl(220, 70%, 60%)', description: 'Frontal EEG (Fp, AF, F)' },
  
  // Central channels (green tones)
  { pattern: /^(fc|c|cp)\d+$/i, color: 'hsl(120, 70%, 50%)', description: 'Central EEG (FC, C, CP)' },
  
  // Parietal channels (yellow-green tones)
  { pattern: /^p\d+$/i, color: 'hsl(80, 70%, 55%)', description: 'Parietal EEG (P)' },
  
  // Occipital channels (red tones)
  { pattern: /^(po|o)\d+$/i, color: 'hsl(0, 70%, 60%)', description: 'Occipital EEG (PO, O)' },
  
  // Temporal channels (purple tones)
  { pattern: /^(ft|t|tp)\d+$/i, color: 'hsl(280, 70%, 60%)', description: 'Temporal EEG (FT, T, TP)' },
  
  // Midline channels (cyan tones)
  { pattern: /^(fpz|afz|fz|fcz|cz|cpz|pz|poz|oz)$/i, color: 'hsl(180, 70%, 55%)', description: 'Midline EEG (z channels)' },
  
  // Reference/Ground (gray tones)
  { pattern: /^(ref|gnd|ground|reference)$/i, color: 'hsl(0, 0%, 50%)', description: 'Reference/Ground' },
  
  // ========== EMG CHANNELS ==========
  
  // EMG channels (orange tones)
  { pattern: /^emg/i, color: 'hsl(30, 80%, 55%)', description: 'EMG (muscle activity)' },
  { pattern: /^(bicep|tricep|quad|gastroc|muscle)/i, color: 'hsl(30, 80%, 55%)', description: 'Muscle names' },
  
  // ========== EOG CHANNELS ==========
  
  // EOG channels (pink tones)
  { pattern: /^(eog|heog|veog)/i, color: 'hsl(330, 70%, 60%)', description: 'EOG (eye movement)' },
  
  // ========== ECG/HR CHANNELS ==========
  
  // ECG/Heart rate (red tones)
  { pattern: /^(ecg|ekg|hr|heart)/i, color: 'hsl(350, 80%, 55%)', description: 'ECG/Heart rate' },
  
  // ========== RESPIRATION ==========
  
  // Respiration (light blue tones)
  { pattern: /^(resp|breath|co2|o2)/i, color: 'hsl(200, 70%, 60%)', description: 'Respiration' },
  
  // ========== GSR/EDA ==========
  
  // Galvanic skin response (yellow tones)
  { pattern: /^(gsr|eda|skin)/i, color: 'hsl(50, 80%, 55%)', description: 'GSR/EDA (skin conductance)' },
  
  // ========== ACCELEROMETER/GYRO ==========
  
  // Accelerometer axes (bright primary colors)
  { pattern: /^(acc|accel).*x/i, color: 'hsl(0, 90%, 50%)', description: 'Accelerometer X-axis' },
  { pattern: /^(acc|accel).*y/i, color: 'hsl(120, 90%, 40%)', description: 'Accelerometer Y-axis' },
  { pattern: /^(acc|accel).*z/i, color: 'hsl(240, 90%, 55%)', description: 'Accelerometer Z-axis' },
  
  // Gyroscope axes (darker primary colors)
  { pattern: /^gyro.*x/i, color: 'hsl(0, 70%, 40%)', description: 'Gyroscope X-axis' },
  { pattern: /^gyro.*y/i, color: 'hsl(120, 70%, 35%)', description: 'Gyroscope Y-axis' },
  { pattern: /^gyro.*z/i, color: 'hsl(240, 70%, 45%)', description: 'Gyroscope Z-axis' },
  
  // ========== POSITION/ORIENTATION ==========
  
  // Position tracking (teal tones)
  { pattern: /^(pos|position|x|y|z)$/i, color: 'hsl(170, 70%, 50%)', description: 'Position coordinates' },
  
  // Quaternion/Rotation (magenta tones)
  { pattern: /^(quat|rot|pitch|roll|yaw)/i, color: 'hsl(300, 70%, 55%)', description: 'Rotation/Orientation' },
  
  // ========== MISC SENSORS ==========
  
  // Temperature (orange-red gradient)
  { pattern: /^temp/i, color: 'hsl(20, 80%, 55%)', description: 'Temperature' },
  
  // Pressure (blue-gray tones)
  { pattern: /^(press|pressure)/i, color: 'hsl(210, 40%, 50%)', description: 'Pressure' },
  
  // Light/Illuminance (bright yellow)
  { pattern: /^(light|lux|illumin)/i, color: 'hsl(60, 90%, 60%)', description: 'Light/Illuminance' },
  
  // Audio/Sound (purple-blue)
  { pattern: /^(audio|sound|mic|volume)/i, color: 'hsl(260, 70%, 55%)', description: 'Audio/Sound' },
];

/**
 * Default color generation settings.
 * Used when no pattern matches.
 */
const DEFAULT_COLOR_CONFIG = {
  saturation: 70,  // Percentage (0-100)
  lightness: 60,   // Percentage (0-100)
  hashSeed: 31,    // Prime number for hash function
};

/**
 * Generate a consistent color for a given channel key.
 * 
 * @param {string} key - Channel identifier (usually "streamName:channelLabel")
 * @returns {string} HSL color string
 */
function getChannelColor(key) {
  // Check cache first
  if (channelColorCache.has(key)) {
    return channelColorCache.get(key);
  }
  
  // Extract just the channel label (after the colon)
  const parts = key.split(':');
  const channelLabel = parts.length > 1 ? parts[1] : key;
  const normalized = channelLabel.trim().toLowerCase();
  
  let color;
  
  // Try to match against pre-defined patterns
  for (const group of COLOR_GROUPS) {
    if (group.pattern instanceof RegExp) {
      if (group.pattern.test(normalized)) {
        color = group.color;
        break;
      }
    } else if (typeof group.pattern === 'string') {
      if (normalized.includes(group.pattern.toLowerCase())) {
        color = group.color;
        break;
      }
    }
  }
  
  // If no pattern matched, generate color from hash
  if (!color) {
    let hash = 0;
    for (let i = 0; i < key.length; i++) {
      hash = (hash * DEFAULT_COLOR_CONFIG.hashSeed + key.charCodeAt(i)) % 360;
    }
    color = `hsl(${hash}, ${DEFAULT_COLOR_CONFIG.saturation}%, ${DEFAULT_COLOR_CONFIG.lightness}%)`;
  }
  
  // Cache and return
  channelColorCache.set(key, color);
  return color;
}

/**
 * Cache to store computed colors.
 * Key: channel identifier, Value: HSL color string
 */
const channelColorCache = new Map();

/**
 * Clear the color cache.
 * Useful if you want to regenerate colors after changing configuration.
 */
function clearColorCache() {
  channelColorCache.clear();
}

/**
 * Get a list of all defined color groups (for documentation/UI purposes).
 * 
 * @returns {Array} Array of color group definitions
 */
function getColorGroups() {
  return COLOR_GROUPS.map(group => ({
    pattern: group.pattern.toString(),
    color: group.color,
    description: group.description
  }));
}

// Export for use in main application
// Note: In browser context without modules, these are automatically global
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    getChannelColor,
    clearColorCache,
    getColorGroups,
    COLOR_GROUPS,
    DEFAULT_COLOR_CONFIG
  };
}
