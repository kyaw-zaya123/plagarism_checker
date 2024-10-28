// app/api/generate_api_key/route.ts
import { NextRequest, NextResponse } from 'next/server'
import { createHash, randomBytes } from 'crypto'
import mysql from 'mysql2/promise'

const pool = mysql.createPool({
  host: '127.0.0.1',
  user: 'root',
  password: 'Kyaw550550#',
  database: 'plagiarism_checker',
  waitForConnections: true,
  connectionLimit: 10,
  queueLimit: 0
})

export async function POST(request: NextRequest) {
  try {
    const { userId } = await request.json()
    
    if (!userId) {
      return NextResponse.json(
        { error: 'User ID is required' },
        { status: 400 }
      )
    }

    // Generate a secure random API key
    const apiKey = generateApiKey()

    // Get connection from the pool
    const connection = await pool.getConnection()

    // Check if user exists
    const [userRows]: any = await connection.execute(
      'SELECT id FROM users WHERE id = ?',
      [userId]
    )

    if (!userRows.length) {
      connection.release()
      return NextResponse.json(
        { error: 'User not found' },
        { status: 404 }
      )
    }

    // Check existing active keys
    const [keyRows]: any = await connection.execute(
      'SELECT COUNT(*) as count FROM api_keys WHERE user_id = ? AND active = 1',
      [userId]
    )

    if (keyRows[0].count >= 5) {
      connection.release()
      return NextResponse.json(
        { error: 'Maximum number of active API keys reached (5)' },
        { status: 400 }
      )
    }

    // Hash the API key before storing it
    const hashedApiKey = createHash('sha256').update(apiKey).digest('hex')

    // Insert new API key
    await connection.execute(
      'INSERT INTO api_keys (user_id, api_key, active, created_at) VALUES (?, ?, 1, NOW())',
      [userId, hashedApiKey]
    )

    connection.release()

    return NextResponse.json({
      message: 'API key generated successfully',
      apiKey // Only send the raw API key once
    })
  } catch (error) {
    console.error('Error generating API key:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}

function generateApiKey(): string {
  // Generate 32 random bytes and convert to hex
  const randomString = randomBytes(32).toString('hex')
  
  // Create a hash of the random string
  const hash = createHash('sha256')
  hash.update(randomString)
  
  // Return first 32 characters of the hash
  return hash.digest('hex').substring(0, 32)
}
