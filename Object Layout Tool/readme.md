# Multi-bin Rectangle Packer (Kerf + Post-fill)

GUI tool for packing axis-aligned rectangles into one or multiple bins, supporting:

- Inner margin between parts
- Edge margin (trim from bin border)
- Kerf (blade thickness)
- 0°/90° rotation option
- Multiple bins
- Post-fill for MaxRects algorithms
- CSV import (w,h[,qty][,id])
- JSON export of placements
- Preview per bin with colors
- Top-left origin toggle

## Requirements

```bash
pip install matplotlib
```
## CSV Format
With header: columns named w, h, optional qty, optional id
Without header: w,h[,qty]
Example:
w,h,qty
50,30,2
80,40,1
