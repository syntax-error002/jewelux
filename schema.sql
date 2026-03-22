-- JEWELUX Database Schema
CREATE DATABASE IF NOT EXISTS jewelux CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE jewelux;

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    phone VARCHAR(20),
    address TEXT,
    city VARCHAR(80),
    country VARCHAR(80) DEFAULT 'India',
    is_admin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Categories table
CREATE TABLE IF NOT EXISTS categories (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    image VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Products table
CREATE TABLE IF NOT EXISTS products (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    slug VARCHAR(200) UNIQUE NOT NULL,
    description TEXT,
    price DECIMAL(10,2) NOT NULL,
    sale_price DECIMAL(10,2),
    stock INT DEFAULT 0,
    category_id INT,
    material VARCHAR(100),
    weight VARCHAR(50),
    dimensions VARCHAR(100),
    is_featured BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL
);

-- Product images table
CREATE TABLE IF NOT EXISTS product_images (
    id INT AUTO_INCREMENT PRIMARY KEY,
    product_id INT NOT NULL,
    image_path VARCHAR(255) NOT NULL,
    is_primary BOOLEAN DEFAULT FALSE,
    sort_order INT DEFAULT 0,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
);

-- Cart table
CREATE TABLE IF NOT EXISTS cart (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    product_id INT NOT NULL,
    quantity INT DEFAULT 1,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
    UNIQUE KEY unique_cart_item (user_id, product_id)
);

-- Wishlist table
CREATE TABLE IF NOT EXISTS wishlist (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    product_id INT NOT NULL,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
    UNIQUE KEY unique_wishlist_item (user_id, product_id)
);

-- Orders table
CREATE TABLE IF NOT EXISTS orders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    order_number VARCHAR(20) UNIQUE NOT NULL,
    total_amount DECIMAL(10,2) NOT NULL,
    status ENUM('pending','confirmed','processing','shipped','delivered','cancelled') DEFAULT 'pending',
    shipping_name VARCHAR(100) NOT NULL,
    shipping_email VARCHAR(150) NOT NULL,
    shipping_phone VARCHAR(20),
    shipping_address TEXT NOT NULL,
    shipping_city VARCHAR(80) NOT NULL,
    shipping_country VARCHAR(80) DEFAULT 'India',
    payment_method VARCHAR(50) DEFAULT 'COD',
    payment_status ENUM('pending','paid','failed','refunded') DEFAULT 'pending',
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Order items table
CREATE TABLE IF NOT EXISTS order_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT NOT NULL,
    product_id INT,
    product_name VARCHAR(200) NOT NULL,
    product_price DECIMAL(10,2) NOT NULL,
    quantity INT NOT NULL,
    subtotal DECIMAL(10,2) NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE SET NULL
);

-- Seed categories
INSERT INTO categories (name, slug, description, image) VALUES
('Rings', 'rings', 'Exquisite rings for every occasion', 'rings.jpg'),
('Necklaces', 'necklaces', 'Elegant necklaces and pendants', 'necklaces.jpg'),
('Earrings', 'earrings', 'Stunning earrings to complement your look', 'earrings.jpg'),
('Bracelets', 'bracelets', 'Luxurious bracelets and bangles', 'bracelets.jpg'),
('Bangles', 'bangles', 'Traditional and modern bangles', 'bangles.jpg'),
('Sets', 'sets', 'Complete jewellery sets', 'sets.jpg');

-- Seed admin user (password: Admin@123)
INSERT INTO users (full_name, email, password_hash, is_admin) VALUES
('Admin User', 'admin@jewelux.com', 'pbkdf2:sha256:260000$placeholder', TRUE);

-- Seed sample products
INSERT INTO products (name, slug, description, price, sale_price, stock, category_id, material, weight, is_featured, is_active) VALUES
('Eternal Diamond Ring', 'eternal-diamond-ring', 'A timeless solitaire diamond ring crafted in 18K white gold. Featuring a brilliant-cut 1.5ct diamond with exceptional clarity and sparkle.', 125000.00, 115000.00, 15, 1, '18K White Gold', '4.2g', TRUE, TRUE),
('Golden Cascade Necklace', 'golden-cascade-necklace', 'An opulent 22K gold necklace with intricate filigree work inspired by royal Mughal jewellery. A statement piece for the discerning woman.', 89000.00, NULL, 8, 2, '22K Gold', '18.5g', TRUE, TRUE),
('Sapphire Drop Earrings', 'sapphire-drop-earrings', 'Elegant sapphire drop earrings set in sterling silver with diamond halos. Perfect for formal occasions.', 45000.00, 39000.00, 20, 3, 'Sterling Silver & Sapphire', '6.8g', TRUE, TRUE),
('Rose Gold Tennis Bracelet', 'rose-gold-tennis-bracelet', 'A stunning tennis bracelet featuring 3ct total weight of diamonds set in 18K rose gold. The epitome of elegance.', 175000.00, NULL, 5, 4, '18K Rose Gold', '12.3g', TRUE, TRUE),
('Pearl Strand Necklace', 'pearl-strand-necklace', 'Lustrous freshwater pearl strand necklace with a 18K gold clasp. Each pearl hand-selected for uniformity and lustre.', 35000.00, 29000.00, 25, 2, 'Freshwater Pearls & 18K Gold', '22g', FALSE, TRUE),
('Diamond Stud Earrings', 'diamond-stud-earrings', 'Classic round brilliant diamond studs in 18K white gold. 0.5ct each, perfect everyday luxury.', 65000.00, NULL, 30, 3, '18K White Gold & Diamonds', '2.1g', TRUE, TRUE),
('Emerald Cocktail Ring', 'emerald-cocktail-ring', 'A bold cocktail ring featuring a 2ct Colombian emerald surrounded by diamonds in 18K yellow gold.', 210000.00, 195000.00, 3, 1, '18K Yellow Gold & Emerald', '8.7g', FALSE, TRUE),
('Gold Charm Bracelet', 'gold-charm-bracelet', 'A delicate 18K gold bracelet with interchangeable charms. Start your collection today.', 28000.00, NULL, 40, 4, '18K Gold', '7.2g', FALSE, TRUE),
('Ruby Pendant Necklace', 'ruby-pendant-necklace', 'A magnificent Burmese ruby pendant surrounded by diamond pavé set in 18K white gold on a delicate chain.', 155000.00, 140000.00, 7, 2, '18K White Gold & Ruby', '5.9g', TRUE, TRUE),
('Diamond Eternity Band', 'diamond-eternity-band', 'A full eternity band featuring F-G colour, VS clarity diamonds in channel setting. 1.2ct total weight.', 95000.00, NULL, 12, 1, '18K White Gold', '3.8g', FALSE, TRUE),
('Antique Gold Bangle Set', 'antique-gold-bangle-set', 'Set of 6 intricately crafted 22K gold bangles with traditional Indian motifs. A treasured heirloom.', 78000.00, 72000.00, 10, 5, '22K Gold', '45g', FALSE, TRUE),
('Diamond & Pearl Jewellery Set', 'diamond-pearl-set', 'Complete bridal set featuring matching necklace, earrings and bracelet with diamonds and pearls.', 320000.00, 285000.00, 2, 6, '18K Gold, Diamonds & Pearls', '68g', TRUE, TRUE);

-- Seed product images (Unsplash CDN — loads directly, no download needed)
INSERT INTO product_images (product_id, image_path, is_primary, sort_order) VALUES
-- 1: Eternal Diamond Ring
(1, 'https://images.unsplash.com/photo-1515562141207-7a88fb7ce338?w=800&q=80&fit=crop', TRUE, 1),
(1, 'https://images.unsplash.com/photo-1605100804763-247f67b3557e?w=800&q=80&fit=crop', FALSE, 2),
-- 2: Golden Cascade Necklace
(2, 'https://images.unsplash.com/photo-1599643478518-a784e5dc4c8f?w=800&q=80&fit=crop', TRUE, 1),
(2, 'https://images.unsplash.com/photo-1611591437281-460bfbe1220a?w=800&q=80&fit=crop', FALSE, 2),
-- 3: Sapphire Drop Earrings
(3, 'https://images.unsplash.com/photo-1630358949869-b8fd3d05c9f5?w=800&q=80&fit=crop', TRUE, 1),
(3, 'https://images.unsplash.com/photo-1588776814546-1ffbb172c4fb?w=800&q=80&fit=crop', FALSE, 2),
-- 4: Rose Gold Tennis Bracelet
(4, 'https://images.unsplash.com/photo-1602173574767-37ac01994b2a?w=800&q=80&fit=crop', TRUE, 1),
(4, 'https://images.unsplash.com/photo-1573408301185-9519f94879aa?w=800&q=80&fit=crop', FALSE, 2),
-- 5: Pearl Strand Necklace
(5, 'https://images.unsplash.com/photo-1596944924616-7b38e7cfac36?w=800&q=80&fit=crop', TRUE, 1),
-- 6: Diamond Stud Earrings
(6, 'https://images.unsplash.com/photo-1535632787350-4e68ef0ac584?w=800&q=80&fit=crop', TRUE, 1),
(6, 'https://images.unsplash.com/photo-1584302179602-e4c3d3fd629d?w=800&q=80&fit=crop', FALSE, 2),
-- 7: Emerald Cocktail Ring
(7, 'https://images.unsplash.com/photo-1602751584552-8ba73aad10e1?w=800&q=80&fit=crop', TRUE, 1),
(7, 'https://images.unsplash.com/photo-1506630268382-8197fce77e07?w=800&q=80&fit=crop', FALSE, 2),
-- 8: Gold Charm Bracelet
(8, 'https://images.unsplash.com/photo-1617038260897-41a1f14a8ca0?w=800&q=80&fit=crop', TRUE, 1),
-- 9: Ruby Pendant Necklace
(9, 'https://images.unsplash.com/photo-1561828995-aa79a2db86dd?w=800&q=80&fit=crop', TRUE, 1),
(9, 'https://images.unsplash.com/photo-1599458252573-56ae36120de1?w=800&q=80&fit=crop', FALSE, 2),
-- 10: Diamond Eternity Band
(10, 'https://images.unsplash.com/photo-1605100804763-247f67b3557e?w=800&q=80&fit=crop', TRUE, 1),
(10, 'https://images.unsplash.com/photo-1515562141207-7a88fb7ce338?w=800&q=80&fit=crop', FALSE, 2),
-- 11: Antique Gold Bangle Set
(11, 'https://images.unsplash.com/photo-1618160702438-9b02ab6515c9?w=800&q=80&fit=crop', TRUE, 1),
(11, 'https://images.unsplash.com/photo-1611591437281-460bfbe1220a?w=800&q=80&fit=crop', FALSE, 2),
-- 12: Diamond & Pearl Jewellery Set
(12, 'https://images.unsplash.com/photo-1522413452208-996ff3f3e740?w=800&q=80&fit=crop', TRUE, 1),
(12, 'https://images.unsplash.com/photo-1573408301185-9519f94879aa?w=800&q=80&fit=crop', FALSE, 2);
