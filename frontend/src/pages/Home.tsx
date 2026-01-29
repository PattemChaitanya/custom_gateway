import { Container, Typography, Button } from "@mui/material";
import { useNavigate } from "react-router-dom";
import useAuthStore from "../hooks/useAuth";
import "./Home.css";

export default function Home() {
    console.log("Home component rendered");
    const profile = useAuthStore((s) => s.profile);
    const navigate = useNavigate();

    return (
        <div className="home-hero">
            <Container maxWidth="lg">
                <div className="hero-grid">
                    <div className="hero-left">
                        <Typography variant="h3" className="hero-title">
                            Simplify Your
                            <br />
                            <span className="accent">API Management</span>
                        </Typography>
                        <Typography variant="body1" className="hero-sub">
                            Easily deploy, monitor, and secure your APIs with our powerful API management
                            platform. Boost your development workflow and ensure seamless API integration.
                        </Typography>
                        <div style={{ marginTop: 24 }}>
                            {profile ? (
                                <Button variant="contained" color="primary" size="large" onClick={() => navigate('/dashboard')}>Go to Dashboard</Button>
                            ) : (
                                <Button variant="contained" color="primary" size="large" onClick={() => navigate('/login')}>Log in</Button>
                            )}
                        </div>
                    </div>

                    <div className="hero-right" aria-hidden>
                        <div className="device-mock">
                            <div className="device-screen">
                                <div className="list">
                                    <div className="row"><span className="pill">/users/authenticate</span><span className="method">GET</span></div>
                                    <div className="row"><span className="pill">/orders</span><span className="method">POST</span></div>
                                    <div className="row"><span className="pill">/payments</span><span className="method">POST</span></div>
                                </div>
                            </div>
                            <div className="device-stand" />
                        </div>
                    </div>
                </div>
            </Container>
        </div>
    );
}
