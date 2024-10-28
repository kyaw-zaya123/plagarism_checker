import { Sequelize } from 'sequelize';

// Create Sequelize instance
const sequelize = new Sequelize('database_name', 'username', 'password', {
  host: 'localhost',
  dialect: 'mysql',
  logging: false,  // Disable logging (optional)
});

sequelize.authenticate()
  .then(() => console.log('Database connected successfully.'))
  .catch((err: any) => console.error('Unable to connect to the database:', err));

export default sequelize;
