# Channel Color Configuration Guide

## Overview

The `colors.js` file controls how channels are colored in the MoBI-View visualization. Colors are assigned based on pattern matching against channel names, allowing for consistent and meaningful color coding across different types of biosignal data.

## How It Works

1. **Pattern Matching**: When a channel is first displayed, its name is checked against a list of pre-defined patterns
2. **First Match Wins**: Patterns are checked in order from top to bottom - the first matching pattern determines the color
3. **Fallback Hash**: If no pattern matches, a color is generated from a hash of the channel name (ensuring consistency across sessions)

## Quick Start: Customizing Colors

### Editing Existing Colors

Open `colors.js` and find the `COLOR_GROUPS` array. Each entry looks like this:

```javascript
{ 
  pattern: /^c\d+$/i,                    // What to match
  color: 'hsl(120, 70%, 50%)',          // What color to use
  description: 'Central EEG (C)'        // Human-readable note
}
```

To change a color, just edit the HSL values:
- **Hue** (0-360): Position on the color wheel (0=red, 120=green, 240=blue)
- **Saturation** (0-100%): Color intensity (0=gray, 100=vivid)
- **Lightness** (0-100%): Brightness (0=black, 50=normal, 100=white)

### Adding New Patterns

Add a new entry to the `COLOR_GROUPS` array:

```javascript
{
  pattern: /^mydevice/i,              // Matches channels starting with "mydevice" (case-insensitive)
  color: 'hsl(180, 80%, 55%)',       // Teal color
  description: 'My custom device'     // Documentation
},
```

**Important**: Add your custom patterns at the **top** of the array to give them priority!

## Pattern Examples

### Simple Text Matching

```javascript
// Matches any channel containing "left"
{ pattern: /left/i, color: 'hsl(0, 70%, 60%)', description: 'Left side' }

// Matches channels starting with "EMG"
{ pattern: /^emg/i, color: 'hsl(30, 80%, 55%)', description: 'EMG channels' }

// Matches channels ending with "_x"
{ pattern: /_x$/i, color: 'hsl(0, 90%, 50%)', description: 'X-axis' }
```

### Complex Patterns

```javascript
// Matches F3, F4, F7, F8, etc. (frontal EEG)
{ pattern: /^f\d+$/i, color: 'hsl(220, 70%, 60%)', description: 'Frontal EEG' }

// Matches Fp1, Fp2, FpZ (frontopolar)
{ pattern: /^fp/i, color: 'hsl(200, 70%, 60%)', description: 'Frontopolar' }

// Matches AccX, AccelX, Accelerometer_X
{ pattern: /^(acc|accel).*x/i, color: 'hsl(0, 90%, 50%)', description: 'Accelerometer X' }
```

## Pattern Syntax Reference

| Pattern | Meaning | Example Match |
|---------|---------|---------------|
| `^` | Start of string | `^eeg` matches "EEG_1" but not "raw_EEG" |
| `$` | End of string | `_x$` matches "Accel_X" but not "X_axis" |
| `\d` | Any digit (0-9) | `c\d+` matches "C3", "C14" |
| `\d+` | One or more digits | `f\d+` matches "F7", "F23" but not "F" |
| `.*` | Any characters | `acc.*x` matches "AccX", "Accel_X" |
| `\|` | OR operator | `(eeg\|meg)` matches "EEG" or "MEG" |
| `[abc]` | Any character in set | `[xyz]` matches "x", "y", or "z" |
| `i` flag | Case-insensitive | `/eeg/i` matches "EEG", "eeg", "Eeg" |

## Pre-Configured Sensor Types

The default configuration includes patterns for:

### Neuroimaging
- **EEG**: Frontal, Central, Parietal, Occipital, Temporal, Midline
- **EOG**: Eye tracking (horizontal/vertical)
- **Reference/Ground**: Gray tones

### Physiological
- **ECG/EKG**: Heart rate and rhythm
- **EMG**: Muscle activity
- **Respiration**: Breathing, CO2, O2
- **GSR/EDA**: Skin conductance

### Motion Tracking
- **Accelerometer**: X/Y/Z axes (bright RGB)
- **Gyroscope**: X/Y/Z axes (darker RGB)
- **Position**: Coordinates and tracking
- **Rotation**: Pitch, roll, yaw, quaternions

### Environmental
- **Temperature**: Orange-red
- **Pressure**: Blue-gray
- **Light**: Bright yellow
- **Audio**: Purple-blue

## Color Palette Recommendations

### High Contrast (for presentations)
- Use saturation 80-90%
- Use lightness 50-60%
- Space hues 30-60° apart

### Subtle (for long viewing sessions)
- Use saturation 40-60%
- Use lightness 55-65%
- Closer hues are fine

### Colorblind-Friendly
- Avoid red-green combinations
- Use blue-yellow or blue-orange
- Vary lightness as well as hue

## Advanced Customization

### Changing Default Hash Colors

Edit the `DEFAULT_COLOR_CONFIG` object:

```javascript
const DEFAULT_COLOR_CONFIG = {
  saturation: 70,  // Make vivid: increase (70-90), make subtle: decrease (40-60)
  lightness: 60,   // Make bright: increase (60-70), make dark: decrease (40-50)
  hashSeed: 31,    // Change for different color distribution
};
```

### Clearing the Color Cache

If you edit `colors.js` while the app is running, reload the page. The colors are cached for performance, so changes won't appear until refresh.

### Debugging

To see all color assignments, open the browser console and run:

```javascript
// See all defined color groups
console.log(getColorGroups());

// Check what color a specific channel gets
console.log(getChannelColor("MyStream:MyChannel"));

// Clear cache and regenerate colors
clearColorCache();
```

## Best Practices

1. **Test with Real Data**: Use actual channel names from your LSL streams when testing patterns
2. **Document Your Patterns**: Use descriptive `description` fields
3. **Order Matters**: Put more specific patterns before general ones
4. **Be Consistent**: Use similar colors for related channels (e.g., all X-axes in red tones)
5. **Consider Context**: Think about how many channels will be displayed simultaneously

## Troubleshooting

**Problem**: My pattern isn't matching

- Check that your regex syntax is correct
- Remember the `i` flag for case-insensitive matching
- Test your pattern in browser console: `/^mypattern$/i.test("MyChannel")`

**Problem**: Wrong pattern is matching

- Remember: **first match wins**
- Move your more specific pattern higher in the array
- Make your pattern more restrictive with `^` and `$`

**Problem**: Colors look too similar

- Increase hue separation (at least 30° apart)
- Vary saturation and lightness as well as hue
- Use the browser DevTools color picker to preview

**Problem**: Changes not appearing

- Hard-refresh the page (Cmd+Shift+R on Mac, Ctrl+Shift+R on Windows)
- Check browser console for JavaScript errors
- Make sure `colors.js` is being loaded (check Network tab)

## Example: Custom EEG Montage

```javascript
// Add this at the TOP of COLOR_GROUPS array
const MY_CUSTOM_COLORS = [
  // Left hemisphere - cool colors
  { pattern: /^(f|c|p|o)[13579]$/i, color: 'hsl(220, 70%, 60%)', description: 'Left hemisphere' },
  
  // Right hemisphere - warm colors
  { pattern: /^(f|c|p|o)[2468]0?$/i, color: 'hsl(30, 70%, 60%)', description: 'Right hemisphere' },
  
  // Midline - neutral colors
  { pattern: /z$/i, color: 'hsl(0, 0%, 70%)', description: 'Midline channels' },
];

// Then merge with existing patterns
const COLOR_GROUPS = [
  ...MY_CUSTOM_COLORS,
  // ... rest of the default patterns
];
```

## Need Help?

- Review the JSDoc comments in `colors.js`
- Check the browser console for errors
- Test patterns at https://regex101.com (select JavaScript flavor)
- See the main README for community support
