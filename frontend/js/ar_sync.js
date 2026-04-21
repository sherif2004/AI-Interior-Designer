/**
 * ar_sync.js — Phase 4A
 * =======================
 * ARSyncCoordinator: translates AR/camera placement world coordinates
 * into RoomState ADD actions and sends them to the backend.
 * All AR placements flow through this class to ensure single write path.
 */

'use strict';

class ARSyncCoordinator {
    constructor(apiClient) {
        this.api    = apiClient;  // reference to window.API or similar
        this._queue = [];
        this._syncing = false;
    }

    /**
     * Place a furniture item from an AR tap/click.
     * @param {string} furnitureType — e.g. "sofa"
     * @param {{x,y,z}} worldPos — 3D world coordinates (metres)
     * @param {number} rotation — degrees
     * @param {string} color
     * @param {object} ikea_product — optional IKEA product data
     */
    async placeFromAR(furnitureType, worldPos, rotation = 0, color = null, ikea_product = null) {
        const action = {
            action: 'ADD',
            params: {
                type:     furnitureType,
                x:        parseFloat(worldPos.x.toFixed(2)),
                z:        parseFloat(worldPos.z.toFixed(2)),
                rotation: Math.round(rotation / 45) * 45, // snap to 45°
                color:    color || '#888888',
                source:   'ar_placement',
            }
        };

        if (ikea_product) {
            action.params.ikea_item_no   = ikea_product.item_no;
            action.params.ikea_name      = ikea_product.name;
            action.params.ikea_price     = ikea_product.price;
            action.params.ikea_currency  = ikea_product.currency;
            action.params.ikea_image_url = ikea_product.image_url;
            action.params.buy_url        = ikea_product.buy_url;
        }

        this._queue.push(action);
        return this._flush();
    }

    /**
     * Move a placed AR furniture item.
     * @param {string} objectId — the assigned room object ID
     * @param {{x,z}} newPos
     */
    async moveFromAR(objectId, newPos) {
        return this._sendAction({
            action: 'MOVE',
            params: { id: objectId, x: newPos.x, z: newPos.z }
        });
    }

    /**
     * Commit an entire AR session's placements to the room state.
     * Called when the user ends an AR session.
     * @param {string} arSessionToken
     */
    async commitSession(arSessionToken) {
        try {
            const res = await fetch(`/ar/session/${arSessionToken}/save-to-design`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
            });
            const data = await res.json();
            window.dispatchEvent(new CustomEvent('ar:session-committed', { detail: data }));
            return data;
        } catch (err) {
            console.error('[ARSync] Session commit error:', err);
            return null;
        }
    }

    /** Flush the action queue to the backend. */
    async _flush() {
        if (this._syncing || this._queue.length === 0) return;
        this._syncing = true;

        while (this._queue.length > 0) {
            const action = this._queue.shift();
            await this._sendAction(action);
        }
        this._syncing = false;
    }

    async _sendAction(action) {
        try {
            // Use the existing /command endpoint (same as chat commands)
            const res = await fetch('/command', {
                method:  'POST',
                headers: { 'Content-Type': 'application/json' },
                body:    JSON.stringify({ action: action.action, params: action.params }),
            });
            const data = await res.json();
            window.dispatchEvent(new CustomEvent('ar:action-applied', { detail: { action, result: data } }));
            return data;
        } catch (err) {
            console.error('[ARSync] Action error:', err, action);
            return null;
        }
    }
}

export { ARSyncCoordinator };
