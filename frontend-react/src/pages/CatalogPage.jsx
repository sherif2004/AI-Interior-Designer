import React, { useState, useEffect } from 'react'
import { getProducts, sendCommand, proxiedImgUrl } from '../api/client'
import '../styles/catalog.css'

export default function CatalogPage() {
  const [products, setProducts] = useState([])
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(false)

  const fetchProducts = async (q) => {
    setLoading(true)
    try {
      const res = await getProducts(q)
      setProducts(res.products)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchProducts('')
  }, [])

  const handleSearch = (e) => {
    e.preventDefault()
    fetchProducts(search)
  }

  return (
    <div className="catalog-layout">
      <div className="catalog-header">
        <h2>IKEA Egypt Catalog</h2>
        <form className="search-bar" onSubmit={handleSearch}>
          <input 
            type="text" 
            className="input-base" 
            placeholder="Search sofas, beds..." 
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <button type="submit" className="btn btn-primary" disabled={loading}>
            {loading ? '...' : 'Search'}
          </button>
        </form>
      </div>

      <div className="product-grid">
        {products.map(p => (
          <ProductCard key={p.id} product={p} />
        ))}
      </div>
    </div>
  )
}

function ProductCard({ product }) {
  const [adding, setAdding] = useState(false)

  const handleAdd = async () => {
    setAdding(true)
    try {
      await sendCommand(`Add a ${product.name} ${product.category}`)
    } catch (e) {
      console.error(e)
    } finally {
      setAdding(false)
    }
  }

  return (
    <div className="product-card">
      <img src={proxiedImgUrl(product.image_url)} alt={product.name} className="product-image" loading="lazy" />
      <div className="product-info">
        <div className="product-title">{product.name}</div>
        <div className="product-series">{product.series || product.category}</div>
        
        <div className="product-price">
          {product.price_usd || product.price_low} EGP
        </div>
        
        <div className="product-dims">
          {product.width}x{product.depth}x{product.height} cm
        </div>

        <button 
          className="btn btn-outline" 
          style={{ width: '100%' }}
          onClick={handleAdd}
          disabled={adding}
        >
          {adding ? 'Adding...' : 'Add to Room'}
        </button>
      </div>
    </div>
  )
}
