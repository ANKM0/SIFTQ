export const COMMON_CSS = `
.error { color: #b00; }
button { font: inherit; }
`;

export const LOGIN_CSS = `
.login {
  align-items: center;
  display: flex;
  justify-content: center;
  min-height: 100vh;
  padding: 24px;
}

.login-card {
  background: #ffffff;
  border: 1px solid #d0d7de;
  border-radius: 8px;
  display: grid;
  gap: 16px;
  max-width: 360px;
  padding: 24px;
  width: 100%;
}

.login-card label {
  display: grid;
  font-size: 14px;
  font-weight: 600;
  gap: 6px;
}

.login-card input {
  border: 1px solid #d0d7de;
  border-radius: 6px;
  font: inherit;
  min-height: 34px;
  padding: 6px 10px;
}
`;
