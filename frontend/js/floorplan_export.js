/**
 * floorplan_export.js — Phase 4C
 * ================================
 * Client-side floor plan export:
 *   PNG  — native Fabric.js toDataURL (2× multiplier for print quality)
 *   SVG  — native Fabric.js toSVG
 *   PDF  — jsPDF (loaded from CDN on demand) wrapping the PNG
 *   DXF  — minimal DXF output for walls (for CAD import)
 */

'use strict';

class FloorplanExport {
    constructor(canvas, wallTool = null) {
        this.canvas   = canvas;   // FloorplanCanvas instance
        this.wallTool = wallTool; // WallTool instance (for DXF export)
    }

    /** Export as PNG (print quality 2×). */
    exportPNG(filename = 'floorplan.png') {
        const dataUrl = this.canvas.canvas?.toDataURL({ format: 'png', multiplier: 2 });
        if (!dataUrl) return;
        this._download(dataUrl, filename);
    }

    /** Export as SVG. */
    exportSVG(filename = 'floorplan.svg') {
        const svg  = this.canvas.canvas?.toSVG();
        if (!svg) return;
        const blob = new Blob([svg], { type: 'image/svg+xml' });
        const url  = URL.createObjectURL(blob);
        this._download(url, filename, true);
    }

    /** Export as PDF using jsPDF (loaded from CDN on demand). */
    async exportPDF(filename = 'floorplan.pdf') {
        await this._loadJsPDF();
        const { jsPDF } = window.jspdf;
        const doc = new jsPDF({ orientation: 'landscape', unit: 'mm', format: 'a4' });

        // Page header
        doc.setFillColor(7, 11, 22);
        doc.rect(0, 0, 297, 210, 'F');

        doc.setTextColor(226, 232, 240);
        doc.setFontSize(18);
        doc.setFont('helvetica', 'bold');
        doc.text('Floor Plan', 148, 18, { align: 'center' });

        doc.setFontSize(10);
        doc.setFont('helvetica', 'normal');
        doc.setTextColor(100, 116, 139);
        doc.text(`Room: ${(this.canvas.roomWidth / 100).toFixed(1)}m × ${(this.canvas.roomDepth / 100).toFixed(1)}m`, 148, 26, { align: 'center' });
        doc.text(`Generated: ${new Date().toLocaleDateString()}`, 148, 31, { align: 'center' });

        // Canvas image
        const imgData = this.canvas.canvas?.toDataURL({ format: 'png', multiplier: 1.5 });
        if (imgData) {
            const imgW = 250, imgH = 150;
            doc.addImage(imgData, 'PNG', (297 - imgW) / 2, 38, imgW, imgH);
        }

        // Legend footer
        doc.setTextColor(71, 85, 105);
        doc.setFontSize(8);
        doc.text('AI Interior Designer — floorplan export', 148, 200, { align: 'center' });

        doc.save(filename);
    }

    /** Export walls as minimal DXF for CAD software. */
    exportDXF(filename = 'floorplan.dxf') {
        const walls = this.wallTool?.getWalls() || [];
        const lines = walls.map(w => {
            const p1 = w.p1_m || { x: 0, z: 0 };
            const p2 = w.p2_m || { x: 1, z: 0 };
            return `0\nLINE\n8\n0\n10\n${p1.x.toFixed(4)}\n20\n${p1.z.toFixed(4)}\n30\n0\n11\n${p2.x.toFixed(4)}\n21\n${p2.z.toFixed(4)}\n31\n0`;
        });

        const dxf = [
            '0\nSECTION\n2\nENTITIES',
            ...lines,
            '0\nENDSEC\n0\nEOF'
        ].join('\n');

        const blob = new Blob([dxf], { type: 'application/dxf' });
        const url  = URL.createObjectURL(blob);
        this._download(url, filename, true);
    }

    /** Try server-side PDF first, fall back to client-side. */
    async exportPDFSmart(filename = 'floorplan.pdf') {
        try {
            const res = await fetch('/floorplan/export?format=pdf');
            if (res.ok) {
                const blob = await res.blob();
                const url  = URL.createObjectURL(blob);
                this._download(url, filename, true);
                return;
            }
        } catch (_) {}
        // Client-side fallback
        await this.exportPDF(filename);
    }

    // ── Helpers ───────────────────────────────────────────────────────────

    _download(urlOrDataUrl, filename, revoke = false) {
        const a = document.createElement('a');
        a.href     = urlOrDataUrl;
        a.download = filename;
        a.style.display = 'none';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        if (revoke) setTimeout(() => URL.revokeObjectURL(urlOrDataUrl), 1000);
    }

    async _loadJsPDF() {
        if (window.jspdf) return;
        await new Promise((res, rej) => {
            const s   = document.createElement('script');
            s.src     = 'https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js';
            s.onload  = res;
            s.onerror = rej;
            document.head.appendChild(s);
        });
    }
}

export { FloorplanExport };
