// app/api/delete_api_key/[userId]/route.ts
import { NextRequest, NextResponse } from 'next/server'
import mysql from 'mysql2/promise'

const pool = mysql.createPool({
  host: '127.0.0.1',
  user: 'root',
  password: 'Kyaw550550#',
  database: 'plagiarism_checker',
  waitForConnections: true,
  connectionLimit: 10,  // Configure as needed
  queueLimit: 0
})

export async function DELETE(
  request: NextRequest,
  { params }: { params: { userId: string } }
) {
  try {
    const { apiKey } = await request.json()
    const userId = params.userId

    if (!apiKey) {
      return NextResponse.json(
        { error: 'API key is required' },
        { status: 400 }
      )
    }

    if (!userId || isNaN(Number(userId))) {
      return NextResponse.json(
        { error: 'Invalid or missing user ID' },
        { status: 400 }
      )
    }

    // Get connection from pool
    const connection = await pool.getConnection()

    // Verify user owns the API key
    const [rows]: any = await connection.execute(
      'SELECT id FROM api_keys WHERE user_id = ? AND api_key = ? AND active = 1 LIMIT 1',
      [userId, apiKey]
    )

    if (!rows.length) {
      connection.release()
      return NextResponse.json(
        { error: 'API key not found or unauthorized' },
        { status: 404 }
      )
    }

    // Deactivate the API key (soft delete)
    await connection.execute(
      'UPDATE api_keys SET active = 0, deactivated_at = NOW() WHERE user_id = ? AND api_key = ?',
      [userId, apiKey]
    )

    connection.release()

    return NextResponse.json({
      message: 'API key deactivated successfully'
    })
  } catch (error) {
    console.error('Error deactivating API key:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}
