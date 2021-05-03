import React, { useState } from 'react'
import { Icon, Loader, Button, Link, Dropdown, CircularLoader } from 'UI'
import { forgotPassword, login } from 'App/routes'
import ReCAPTCHA from 'react-google-recaptcha'
import stl from './signup.css'
import cn from 'classnames'
import { signup, fetchTenants } from 'Duck/user';
import { connect } from 'react-redux'

const FORGOT_PASSWORD = forgotPassword()
const LOGIN_ROUTE = login()
const recaptchaRef = React.createRef()

@connect(
  state => ({
    tenants: state.getIn(['user', 'tenants']),
    errors: state.getIn([ 'user', 'signupRequest', 'errors' ]),
    loading: state.getIn([ 'user', 'signupRequest', 'loading' ]),
  }),
  { signup, fetchTenants },
)
export default class SignupForm extends React.Component {

  state = {
    tenantId: '',
    fullname: '',
    password: '',
    email: '',
    projectName: '',
    organizationName: '',
  };

  componentDidMount() {
    this.props.fetchTenants();
  }

  handleSubmit = (token) => {
    const { tenantId, fullname, password, email, projectName, organizationName, auth } = this.state;
    this.props.signup({ tenantId, fullname, password, email, projectName, organizationName, auth, 'g-recaptcha-response': token })
  }

  write = ({ target: { value, name } }) => this.setState({ [ name ]: value })
  writeOption = (e, { name, value }) => this.setState({ [ name ]: value });

  onSubmit = (e) => {
    e.preventDefault();
    if (window.ENV.CAPTCHA_ENABLED && recaptchaRef.current) {
      recaptchaRef.current.execute();      
    } else if (!window.ENV.CAPTCHA_ENABLED) {
      this.handleSubmit();
    }
  }
  render() {
    const { loading, errors, tenants } = this.props;

    return (
      <form onSubmit={ this.onSubmit }>
        <div className="mb-8">
          <h2 className="text-center text-3xl mb-6">Get Started</h2>
          <div className="text-center text-xl">Already having an account? <span className="link"><Link to={ LOGIN_ROUTE }>Sign In</Link></span></div>
        </div>
        <>
          { window.ENV.CAPTCHA_ENABLED && (
            <ReCAPTCHA
              ref={ recaptchaRef }
              size="invisible"
              sitekey={ window.ENV.CAPTCHA_SITE_KEY }
              onChange={ token => this.handleSubmit(token) }
            />
          )}
          <div>
            { tenants.length > 0 && (
              <div className="mb-6">
                <label>Existing Accounts</label>
                <div className={ stl.inputWithIcon }>              
                  <Dropdown
                    className="w-full"
                    placeholder="Select tenant"
                    selection
                    options={ tenants }
                    name="tenantId"
                    // value={ instance.currentPeriod }
                    onChange={ this.writeOption }
                  />
                </div>
              </div>
            )}
            <div className="mb-6">
              <label>Email</label>
              <div className={ stl.inputWithIcon }>              
                <input
                  autoFocus={true}
                  autoComplete="username"
                  type="email"
                  placeholder="E.g. email@yourcompany.com"
                  name="email"
                  onChange={ this.write }
                  className={ stl.email }
                  required="true"
                />
              </div>
            </div>
            <div className="mb-6">
              <label className="mb-2">Create Password</label>
              <div className={ stl.inputWithIcon }>            
                <input
                  type="password"
                  placeholder="Min 8 Characters"
                  minLength="8"
                  name="password"
                  onChange={ this.write }
                  className={ stl.password }
                  required="true"
                />
              </div>
            </div>
            <div className="mb-6">
              <label>Your Name</label>
              <div className={ stl.inputWithIcon }>              
                <input                
                  type="text"
                  placeholder="E.g John Doe"
                  name="fullname"
                  onChange={ this.write }
                  className={ stl.email }
                  required="true"
                />
              </div>
            </div>
  
            <div className="mb-6">
              <label>Organization Name</label>
              <div className={ stl.inputWithIcon }>              
                <input                
                  type="text"
                  placeholder="E.g Uber"
                  name="organizationName"
                  onChange={ this.write }
                  className={ stl.email }
                  required="true"
                />
              </div>
            </div>

            <div className="mb-6">
              <div className="text-sm">By creating an account, you agree to our <a href="https://openreplay.com/terms.html" className="link">Terms of Service</a> and <a href="https://openreplay.com/privacy.html" className="link">Privacy Policy</a></div>
            </div>

          </div>
        </>
        { errors &&
          <div className={ stl.errors }>
            { errors.map(error => (
              <div className={stl.errorItem}>
                <Icon name="info" color="red" size="20"/>
                <span className="color-red ml-2">{ error }<br /></span>
              </div>
            )) }
          </div>
        }
        <div className={ stl.formFooter }>
          <Button type="submit" primary >
            { loading ? 
              <CircularLoader loading={true} /> :
              'Signup' 
            }
          </Button>
  
          {/* <div className={ cn(stl.links, 'text-lg') }>
            <Link to={ LOGIN_ROUTE }>{'Back to Login'}</Link>
          </div> */}
        </div>
      </form>
    )
  }
}

// export default connect(state => ({
//   errors: state.getIn([ 'user', 'signupRequest', 'errors' ]),
//   loading: state.getIn([ 'user', 'signupRequest', 'loading' ]),
// }), { signup })(SignupForm)